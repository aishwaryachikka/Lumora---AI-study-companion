"""Mocked unit tests for lecture media extraction and transcription."""

import os
from pathlib import Path
import shutil
import subprocess

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.config import Settings
from app.api.routes import documents as document_routes
from app.services.embeddings import EmbeddingService, MockEmbeddingProvider
from app.services.rag import EvidenceGroundedAnswerService, MockAnswerProvider
from app.services.retrieval import RetrievalService
from app.services.tutor import TutorChatService
from app.services.vector_store import InMemoryVectorStore
from app.services.video_processing import (
    EmptyAudioError,
    FFmpegAudioExtractor,
    FFmpegUnavailableError,
    LectureMediaProcessor,
    MediaAudioInfo,
    MediaDurationLimitError,
    MediaProcessingTimeoutError,
    MediaTooLargeError,
    OpenAICompatibleTranscriber,
    TranscriptionProviderError,
    TranscriptSpan,
    TranscriptionTimeoutError,
    TranscriptionResult,
    TranscriptionSegment,
    UnsupportedCodecError,
    UnsupportedMediaTypeError,
    is_supported_media_type,
)


class FakeAudioExtractor:
    """Deterministic audio extractor for unit tests without FFmpeg."""

    def __init__(self, info: MediaAudioInfo | None = None, audio_data: bytes = b"mock audio") -> None:
        self.info = info or MediaAudioInfo(duration_seconds=60.0, timeline_start_seconds=0.0)
        self.audio_data = audio_data
        self.received_limits: tuple[float, float] | None = None

    def extract_audio(
        self,
        media_path: Path,
        audio_path: Path,
        *,
        max_duration_seconds: float,
        timeout_seconds: float,
    ) -> MediaAudioInfo:
        self.received_limits = (max_duration_seconds, timeout_seconds)
        audio_path.write_bytes(self.audio_data)
        if self.info.duration_seconds > max_duration_seconds:
            raise MediaDurationLimitError("too long")
        return self.info


class FakeTranscriber:
    """Mock transcription provider returning a fixed response."""

    def __init__(self, segments: list[TranscriptSpan]) -> None:
        self.segments = segments
        self.received_audio: Path | None = None

    def transcribe(self, audio_path: Path) -> list[TranscriptSpan]:
        self.received_audio = audio_path
        assert audio_path.is_file()
        return self.segments


def test_mocked_transcription_preserves_segments_and_source_timestamps(tmp_path: Path) -> None:
    """Provider timestamps are offset to the source timeline and formatted."""
    media_path = tmp_path / "lesson.mp4"
    media_path.write_bytes(b"mock media")
    extractor = FakeAudioExtractor(MediaAudioInfo(90, 2.5))
    transcriber = FakeTranscriber(
        [
            TranscriptSpan("Welcome to biology.", 0.25, 1.5),
            TranscriptSpan("Today we study cells.", 2.0, 3.25),
        ]
    )
    processor = LectureMediaProcessor(
        transcriber,
        audio_extractor=extractor,
        max_duration_seconds=120,
    )

    result = processor.process_path(
        media_path,
        "lesson.mp4",
        document_id="doc-lecture",
        source_id="upload-3",
    )

    assert result.status == "transcribed"
    assert result.source_filename == "lesson.mp4"
    assert result.source_type == "video/mp4"
    assert result.duration_seconds == 90
    assert result.segments[0].text == "Welcome to biology."
    assert result.segments[0].start_seconds == 2.75
    assert result.segments[0].end_seconds == 4.0
    assert result.segments[0].formatted_start_time == "00:00:02.750"
    assert result.segments[0].formatted_end_time == "00:00:04.000"
    assert result.segments[0].source_filename == "lesson.mp4"
    assert result.segments[0].source_type == "video/mp4"
    assert result.source_segments[1].timestamp_start_seconds == 4.5
    assert result.source_segments[1].document_id == "doc-lecture"
    assert result.source_segments[1].source_id == "upload-3"
    assert transcriber.received_audio is not None
    assert not transcriber.received_audio.exists()  # temporary audio is cleaned up


def test_audio_media_and_no_speech_are_supported(tmp_path: Path) -> None:
    """Audio-only formats return an explicit no-speech result when empty."""
    media_path = tmp_path / "lecture.wav"
    media_path.write_bytes(b"mock wav")

    result = LectureMediaProcessor(
        FakeTranscriber([]),
        audio_extractor=FakeAudioExtractor(),
    ).process_path(media_path, "lecture.wav")

    assert result.status == "no_speech"
    assert result.segments == []
    assert result.source_type == "audio/wav"


def test_unsupported_type_and_file_size_are_rejected(tmp_path: Path) -> None:
    """Unsupported extensions and oversized files fail before transcription."""
    invalid = tmp_path / "notes.txt"
    invalid.write_bytes(b"text")
    large = tmp_path / "lecture.mp3"
    large.write_bytes(b"more than one byte")
    processor = LectureMediaProcessor(FakeTranscriber([]), max_file_size_bytes=1, audio_extractor=FakeAudioExtractor())

    with pytest.raises(UnsupportedMediaTypeError):
        processor.process_path(invalid, "notes.txt")
    with pytest.raises(MediaTooLargeError):
        processor.process_path(large, "lecture.mp3")


def test_common_media_type_aliases_are_accepted() -> None:
    """Browser and operating-system MIME aliases remain usable for supported files."""
    assert is_supported_media_type(".opus", "audio/ogg")
    assert is_supported_media_type(".mkv", "application/x-matroska")
    assert not is_supported_media_type(".mp4", "application/pdf")


def test_duration_limit_is_passed_to_extractor_and_enforced(tmp_path: Path) -> None:
    """Duration limits are applied before transcription begins."""
    media_path = tmp_path / "lecture.webm"
    media_path.write_bytes(b"media")
    extractor = FakeAudioExtractor(MediaAudioInfo(121, 0))
    transcriber = FakeTranscriber([])

    with pytest.raises(MediaDurationLimitError):
        LectureMediaProcessor(
            transcriber,
            max_duration_seconds=120,
            audio_extractor=extractor,
        ).process_path(media_path, "lecture.webm")
    assert extractor.received_limits is not None
    assert extractor.received_limits[0] == 120
    assert transcriber.received_audio is None


def test_extracted_audio_size_limit_is_enforced(tmp_path: Path) -> None:
    """Oversized temporary audio is rejected before contacting the provider."""
    media_path = tmp_path / "lecture.mp3"
    media_path.write_bytes(b"media")
    transcriber = FakeTranscriber([])

    with pytest.raises(MediaTooLargeError):
        LectureMediaProcessor(
            transcriber,
            max_audio_size_bytes=1,
            audio_extractor=FakeAudioExtractor(audio_data=b"too large"),
        ).process_path(media_path, "lecture.mp3")
    assert transcriber.received_audio is None


def test_missing_extracted_audio_is_reported(tmp_path: Path) -> None:
    """An empty extraction result is not sent to the transcription provider."""
    media_path = tmp_path / "lecture.mp3"
    media_path.write_bytes(b"media")
    transcriber = FakeTranscriber([])

    with pytest.raises(EmptyAudioError):
        LectureMediaProcessor(
            transcriber,
            audio_extractor=FakeAudioExtractor(audio_data=b""),
        ).process_path(media_path, "lecture.mp3")
    assert transcriber.received_audio is None


def test_missing_ffmpeg_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """FFmpeg availability is checked before probing or transcription."""
    monkeypatch.setattr(shutil, "which", lambda _: None)

    with pytest.raises(FFmpegUnavailableError):
        FFmpegAudioExtractor().extract_audio(
            tmp_path / "input.mp4",
            tmp_path / "audio.mp3",
            max_duration_seconds=60,
            timeout_seconds=5,
        )


def test_ffprobe_detects_no_audio_stream(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A media container without audio returns a typed empty-audio error."""
    monkeypatch.setattr(shutil, "which", lambda name: name)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout='{"streams": []}', stderr=""),
    )

    with pytest.raises(EmptyAudioError):
        FFmpegAudioExtractor().extract_audio(
            tmp_path / "silent.mp4",
            tmp_path / "audio.mp3",
            max_duration_seconds=60,
            timeout_seconds=5,
        )


def test_ffprobe_failure_is_reported_as_unsupported_codec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Unreadable and unsupported media does not expose FFmpeg stderr."""
    monkeypatch.setattr(shutil, "which", lambda name: name)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="private parser output"),
    )

    with pytest.raises(UnsupportedCodecError) as error:
        FFmpegAudioExtractor().extract_audio(
            tmp_path / "broken.mkv",
            tmp_path / "audio.mp3",
            max_duration_seconds=60,
            timeout_seconds=5,
        )
    assert "private parser output" not in str(error.value)


def test_ffprobe_timeout_is_typed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Long media probing stops at the configured FFmpeg timeout."""
    monkeypatch.setattr(shutil, "which", lambda name: name)

    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("ffprobe", 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(MediaProcessingTimeoutError):
        FFmpegAudioExtractor().extract_audio(
            tmp_path / "slow.mp4",
            tmp_path / "audio.mp3",
            max_duration_seconds=60,
            timeout_seconds=1,
        )


def test_whisper_compatible_provider_parses_mocked_response(tmp_path: Path) -> None:
    """A mocked Whisper-compatible API response yields timestamped spans."""
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"mock audio")

    def mock_api(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-secret"
        return httpx.Response(
            200,
            json={
                "segments": [
                    {"start": 0.4, "end": 1.2, "text": "First phrase."},
                    {"start": 1.5, "end": 2.1, "text": "Second phrase."},
                ]
            },
        )

    provider = OpenAICompatibleTranscriber(
        "http://localhost:8001/v1/audio/transcriptions",
        "whisper-local",
        api_key="test-secret",
        transport=httpx.MockTransport(mock_api),
    )
    spans = provider.transcribe(audio_path)

    assert spans == [
        TranscriptSpan("First phrase.", 0.4, 1.2),
        TranscriptSpan("Second phrase.", 1.5, 2.1),
    ]


def test_provider_timeout_and_invalid_response_are_typed(tmp_path: Path) -> None:
    """Provider timeouts and missing timestamps do not leak response content."""
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"audio")
    timeout_provider = OpenAICompatibleTranscriber(
        "http://localhost/transcribe",
        "local",
        transport=httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("private"))),
    )
    with pytest.raises(TranscriptionTimeoutError):
        timeout_provider.transcribe(audio_path)

    invalid_provider = OpenAICompatibleTranscriber(
        "http://localhost/transcribe",
        "local",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"text": "No timestamps"})),
    )
    with pytest.raises(TranscriptionProviderError):
        invalid_provider.transcribe(audio_path)


def test_media_upload_route_returns_transcript_without_real_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ingestion route returns the timestamped schema with a mocked processor."""
    class StubMediaProcessor:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def process_path(
            self,
            media_path: Path,
            filename: str,
            *,
            document_id: str | None = None,
            source_id: str | None = None,
        ) -> TranscriptionResult:
            assert media_path.is_file()
            return TranscriptionResult(
                source_filename=filename,
                source_type="video/mp4",
                status="transcribed",
                duration_seconds=10,
                document_id=document_id,
                source_id=source_id,
                segments=[
                    TranscriptionSegment(
                        text="Mocked lecture segment",
                        start_seconds=1.0,
                        end_seconds=2.0,
                        formatted_start_time="00:00:01.000",
                        formatted_end_time="00:00:02.000",
                        source_filename=filename,
                        source_type="video/mp4",
                        segment_id="transcript-1",
                    )
                ],
            )

    monkeypatch.setattr(document_routes, "LectureMediaProcessor", StubMediaProcessor)
    vector_store = InMemoryVectorStore()
    embeddings = EmbeddingService(
        MockEmbeddingProvider(8),
        model_id="test-mock-model",
        expected_dimensions=8,
    )
    tutor = TutorChatService(
        RetrievalService(embeddings, vector_store),
        EvidenceGroundedAnswerService(MockAnswerProvider()),
    )
    response = TestClient(create_app(tutor)).post(
        "/api/documents/upload/media",
        data={"document_id": "doc-1", "source_id": "source-1"},
        files={"file": ("lesson.mp4", b"mock media", "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["segments"][0]["text"] == "Mocked lecture segment"
    assert payload["segments"][0]["start_seconds"] == 1.0
    assert payload["segments"][0]["formatted_end_time"] == "00:00:02.000"


@pytest.mark.integration
def test_optional_real_transcription_with_local_sample() -> None:
    """Opt-in integration test; normal test runs never make provider calls."""
    if os.getenv("LUMORA_RUN_STT_INTEGRATION") != "1":
        pytest.skip("set LUMORA_RUN_STT_INTEGRATION=1 to enable actual transcription")
    sample = os.getenv("LUMORA_TEST_MEDIA_FILE")
    if not sample or not Path(sample).is_file():
        pytest.skip("set LUMORA_TEST_MEDIA_FILE to a small local lecture sample")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and ffprobe are required for this optional integration test")

    settings = Settings()
    if settings.stt_provider not in {"openai_compatible", "whisper_compatible"}:
        pytest.skip("the optional integration currently uses the configured Whisper-compatible HTTP endpoint")
    api_key = settings.stt_api_key.get_secret_value() if settings.stt_api_key else None
    processor = LectureMediaProcessor(
        OpenAICompatibleTranscriber(settings.stt_api_url, settings.stt_model, api_key, settings.stt_timeout_seconds),
        max_file_size_bytes=settings.max_upload_size_bytes,
        max_duration_seconds=settings.max_media_duration_seconds,
        max_audio_size_bytes=settings.max_extracted_audio_size_bytes,
        ffmpeg_path=settings.ffmpeg_path,
        ffprobe_path=settings.ffprobe_path,
        ffmpeg_timeout_seconds=settings.ffmpeg_timeout_seconds,
    )
    result = processor.process_path(Path(sample), Path(sample).name)
    assert result.status in {"transcribed", "no_speech"}
