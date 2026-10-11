"""Lecture audio extraction and Whisper-compatible transcription services."""

from dataclasses import dataclass
import json
import logging
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Literal, Protocol

import httpx

from app.services.chunking import SourceSegment
from app.services.document_processing import DocumentProcessingError

logger = logging.getLogger(__name__)

SUPPORTED_MEDIA_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".m4v": "video/x-m4v",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
}
MEDIA_TYPE_ALIASES: dict[str, set[str]] = {
    ".mkv": {"video/matroska", "application/x-matroska"},
    ".m4v": {"video/mp4"},
    ".wav": {"audio/x-wav", "audio/wave"},
    ".m4a": {"audio/x-m4a"},
    ".aac": {"audio/mp4"},
    ".ogg": {"application/ogg"},
    ".opus": {"audio/ogg", "application/ogg"},
}


def is_supported_media_type(extension: str, content_type: str | None) -> bool:
    """Check declared media type against an extension, allowing common aliases."""
    if content_type in {None, "application/octet-stream"}:
        return True
    canonical = SUPPORTED_MEDIA_TYPES.get(extension.lower())
    return content_type == canonical or content_type in MEDIA_TYPE_ALIASES.get(extension.lower(), set())


class MediaProcessingError(DocumentProcessingError):
    """Base class for lecture media validation and processing errors."""

    code = "media_processing_error"


class UnsupportedMediaTypeError(MediaProcessingError):
    """The filename or media contents are not a supported audio/video type."""

    code = "unsupported_media_type"
    status_code = 415


class MediaTooLargeError(MediaProcessingError):
    """The input media or extracted audio exceeds a configured limit."""

    code = "media_too_large"
    status_code = 413


class MediaDurationLimitError(MediaProcessingError):
    """The media duration exceeds the configured processing limit."""

    code = "media_duration_limit"
    status_code = 413


class FFmpegUnavailableError(MediaProcessingError):
    """FFmpeg or ffprobe is missing or unavailable on the configured path."""

    code = "ffmpeg_unavailable"
    status_code = 503


class MediaProcessingTimeoutError(MediaProcessingError):
    """FFmpeg or ffprobe exceeded its configured execution timeout."""

    code = "media_processing_timeout"
    status_code = 504


class EmptyAudioError(MediaProcessingError):
    """No usable audio stream or audio samples were found."""

    code = "empty_audio"
    status_code = 422


class UnsupportedCodecError(MediaProcessingError):
    """FFmpeg could not decode or encode the media audio stream."""

    code = "unsupported_codec"
    status_code = 422


class TranscriptionConfigurationError(MediaProcessingError):
    """The selected transcription provider is missing required configuration."""

    code = "transcription_not_configured"
    status_code = 503


class TranscriptionTimeoutError(MediaProcessingError):
    """The transcription provider exceeded its configured timeout."""

    code = "transcription_timeout"
    status_code = 504


class TranscriptionProviderError(MediaProcessingError):
    """The configured transcription provider failed or returned invalid data."""

    code = "transcription_failed"
    status_code = 502


@dataclass(frozen=True)
class TranscriptSpan:
    """Provider transcript segment with seconds relative to extracted audio."""

    text: str
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class TranscriptionSegment:
    """Transcript segment with source metadata and original media timestamps."""

    text: str
    start_seconds: float
    end_seconds: float
    formatted_start_time: str
    formatted_end_time: str
    source_filename: str
    source_type: str
    segment_id: str


@dataclass(frozen=True)
class TranscriptionResult:
    """Media transcription result ready for the common chunking pipeline."""

    source_filename: str
    source_type: str
    status: Literal["transcribed", "no_speech"]
    duration_seconds: float
    segments: list[TranscriptionSegment]
    document_id: str | None = None
    source_id: str | None = None

    @property
    def source_segments(self) -> list[SourceSegment]:
        """Return transcript segments as source-aware inputs for the chunker."""
        return [
            SourceSegment(
                text=segment.text,
                source_filename=segment.source_filename,
                source_type=segment.source_type,
                document_id=self.document_id,
                source_id=self.source_id,
                segment_id=segment.segment_id,
                timestamp_start_seconds=segment.start_seconds,
                timestamp_end_seconds=segment.end_seconds,
            )
            for segment in self.segments
        ]


@dataclass(frozen=True)
class MediaAudioInfo:
    """Probe details needed to preserve the input media timeline."""

    duration_seconds: float
    timeline_start_seconds: float


class AudioExtractor(Protocol):
    """Interface implemented by FFmpeg or test audio extraction adapters."""

    def extract_audio(
        self,
        media_path: Path,
        audio_path: Path,
        *,
        max_duration_seconds: float,
        timeout_seconds: float,
    ) -> MediaAudioInfo:
        """Extract the first audio stream and return its source timeline bounds."""
        ...


class SpeechToTextProvider(Protocol):
    """Whisper-compatible transcription provider interface."""

    def transcribe(self, audio_path: Path) -> list[TranscriptSpan]:
        """Transcribe an audio file into timestamped segments."""
        ...


class FFmpegAudioExtractor:
    """Probe lecture media and extract normalized mono audio using FFmpeg."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def extract_audio(
        self,
        media_path: Path,
        audio_path: Path,
        *,
        max_duration_seconds: float,
        timeout_seconds: float,
    ) -> MediaAudioInfo:
        """Probe duration and extract 16 kHz mono MP3, preserving timeline offset."""
        ffmpeg = shutil.which(self.ffmpeg_path)
        ffprobe = shutil.which(self.ffprobe_path)
        if not ffmpeg or not ffprobe:
            raise FFmpegUnavailableError("FFmpeg and ffprobe must both be installed and available on PATH.")

        probe_command = [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration,start_time:stream=codec_type,start_time,duration",
            "-of", "json",
            str(media_path),
        ]
        try:
            probe = subprocess.run(
                probe_command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MediaProcessingTimeoutError("Media probing exceeded the configured timeout.") from exc
        except OSError as exc:
            raise FFmpegUnavailableError("ffprobe could not be started.") from exc
        if probe.returncode != 0:
            logger.warning("ffprobe rejected media filename=%s", media_path.name)
            raise UnsupportedCodecError("The media file is malformed or uses an unsupported codec.")
        try:
            metadata = json.loads(probe.stdout)
            if not isinstance(metadata, dict):
                raise UnsupportedCodecError("The media probe returned invalid metadata.")
            audio_streams = [
                stream
                for stream in metadata.get("streams", [])
                if isinstance(stream, dict) and stream.get("codec_type") == "audio"
            ]
            if not audio_streams:
                raise EmptyAudioError("No audio stream was found in the uploaded media.")
            audio_stream = audio_streams[0]
            format_info = metadata.get("format", {})
            if not isinstance(format_info, dict):
                format_info = {}
            duration = self._first_finite_number(format_info.get("duration"), audio_stream.get("duration"))
            timeline_start = self._first_finite_number(
                audio_stream.get("start_time"),
                format_info.get("start_time"),
                default=0.0,
            )
            if duration is None:
                raise UnsupportedCodecError("The media duration is unavailable.")
        except MediaProcessingError:
            raise
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise UnsupportedCodecError("The media duration or audio metadata is unavailable.") from exc
        if duration <= 0:
            raise EmptyAudioError("The media contains no usable audio duration.")
        if duration > max_duration_seconds:
            raise MediaDurationLimitError("The media exceeds the configured duration limit.")

        extraction_command = [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-v", "error",
            "-i", str(media_path),
            "-map", "0:a:0",
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            "-f", "mp3",
            "-y", str(audio_path),
        ]
        try:
            extraction = subprocess.run(
                extraction_command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MediaProcessingTimeoutError("Audio extraction exceeded the configured timeout.") from exc
        except OSError as exc:
            raise FFmpegUnavailableError("FFmpeg could not be started.") from exc
        if extraction.returncode != 0:
            logger.warning("ffmpeg could not extract audio filename=%s", media_path.name)
            raise UnsupportedCodecError("FFmpeg could not decode the media audio stream.")
        if not audio_path.is_file() or audio_path.stat().st_size == 0:
            raise EmptyAudioError("FFmpeg produced an empty audio file.")
        return MediaAudioInfo(duration_seconds=duration, timeline_start_seconds=timeline_start)

    @staticmethod
    def _first_finite_number(*values: Any, default: float | None = None) -> float | None:
        """Parse the first valid finite number from ffprobe's nullable fields."""
        for value in values:
            try:
                number = float(value)
            except (ValueError, TypeError):
                continue
            if math.isfinite(number):
                return number
        return default


class OpenAICompatibleTranscriber:
    """Call a Whisper-compatible `/audio/transcriptions` HTTP endpoint."""

    def __init__(
        self,
        api_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 300,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_url = api_url
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def transcribe(self, audio_path: Path) -> list[TranscriptSpan]:
        """Submit audio and parse verbose JSON segment timestamps.

        HTTP response bodies, authorization values, and transcript text are
        deliberately excluded from logs and client-facing exceptions.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            with audio_path.open("rb") as audio_file, httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    self.api_url,
                    headers=headers,
                    data={"model": self.model, "response_format": "verbose_json"},
                    files={"file": (audio_path.name, audio_file, "audio/mpeg")},
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise TranscriptionProviderError("The provider returned an invalid transcription response.")
            segments = payload.get("segments")
            if not isinstance(segments, list):
                raise TranscriptionProviderError("The provider did not return timestamped transcript segments.")
            result: list[TranscriptSpan] = []
            for item in segments:
                if not isinstance(item, dict):
                    raise TranscriptionProviderError("The provider returned an invalid transcript segment.")
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                start = float(item["start"])
                end = float(item["end"])
                if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
                    raise TranscriptionProviderError("The provider returned invalid transcript timestamps.")
                result.append(TranscriptSpan(text=text, start_seconds=start, end_seconds=end))
            return result
        except httpx.TimeoutException as exc:
            raise TranscriptionTimeoutError("The transcription provider timed out.") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Transcription provider returned HTTP status=%d", exc.response.status_code)
            raise TranscriptionProviderError("The transcription provider rejected the audio request.") from exc
        except httpx.RequestError as exc:
            logger.warning("Transcription provider request failed type=%s", type(exc).__name__)
            raise TranscriptionProviderError("The transcription provider is unavailable.") from exc
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            raise TranscriptionProviderError("The transcription provider returned an invalid response.") from exc


def format_timestamp(seconds: float) -> str:
    """Format non-negative seconds as `HH:MM:SS.mmm`."""
    milliseconds = round(seconds * 1000)
    total_seconds, millis = divmod(milliseconds, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{millis:03d}"


class LectureMediaProcessor:
    """Coordinate bounded FFmpeg extraction and injected speech transcription."""

    def __init__(
        self,
        transcriber: SpeechToTextProvider,
        *,
        max_file_size_bytes: int = 25 * 1024 * 1024,
        max_duration_seconds: float = 1800,
        max_audio_size_bytes: int = 100 * 1024 * 1024,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        ffmpeg_timeout_seconds: float = 300,
        audio_extractor: AudioExtractor | None = None,
    ) -> None:
        if min(max_file_size_bytes, max_duration_seconds, max_audio_size_bytes, ffmpeg_timeout_seconds) <= 0:
            raise ValueError("Media processing limits must be positive")
        self.transcriber = transcriber
        self.max_file_size_bytes = max_file_size_bytes
        self.max_duration_seconds = max_duration_seconds
        self.max_audio_size_bytes = max_audio_size_bytes
        self.ffmpeg_timeout_seconds = ffmpeg_timeout_seconds
        self.audio_extractor = audio_extractor or FFmpegAudioExtractor(ffmpeg_path, ffprobe_path)

    def process_path(
        self,
        media_path: Path,
        filename: str,
        *,
        document_id: str | None = None,
        source_id: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe supported video/audio, retaining original media timestamps."""
        safe_filename = Path(filename.replace("\\", "/")).name
        extension = Path(safe_filename).suffix.lower()
        source_type = SUPPORTED_MEDIA_TYPES.get(extension)
        if source_type is None:
            raise UnsupportedMediaTypeError("The uploaded audio or video format is not supported.")
        try:
            file_size = media_path.stat().st_size
        except OSError as exc:
            raise UnsupportedMediaTypeError("The uploaded media could not be read.") from exc
        if file_size == 0:
            raise EmptyAudioError("The uploaded media file is empty.")
        if file_size > self.max_file_size_bytes:
            raise MediaTooLargeError("The media exceeds the configured upload size limit.")

        try:
            with tempfile.TemporaryDirectory(prefix="lumora-audio-") as temp_dir:
                audio_path = Path(temp_dir) / "audio.mp3"
                audio_info = self.audio_extractor.extract_audio(
                    media_path,
                    audio_path,
                    max_duration_seconds=self.max_duration_seconds,
                    timeout_seconds=self.ffmpeg_timeout_seconds,
                )
                if not audio_path.is_file() or audio_path.stat().st_size == 0:
                    raise EmptyAudioError("The extracted audio file is empty or unavailable.")
                if audio_path.stat().st_size > self.max_audio_size_bytes:
                    raise MediaTooLargeError("The extracted audio exceeds the configured processing size limit.")
                try:
                    provider_segments = self.transcriber.transcribe(audio_path)
                except DocumentProcessingError:
                    raise
                except Exception as exc:
                    logger.warning("Transcription failed provider_error_type=%s", type(exc).__name__)
                    raise TranscriptionProviderError("The configured transcription provider failed.") from exc
        except DocumentProcessingError:
            raise
        except Exception as exc:
            logger.exception("Lecture media processing failed filename=%s", safe_filename)
            raise MediaProcessingError("The media could not be processed.") from exc

        segments: list[TranscriptionSegment] = []
        if not isinstance(provider_segments, list):
            raise TranscriptionProviderError("The transcription provider returned invalid segments.")
        for index, item in enumerate(provider_segments, start=1):
            text = item.text.strip()
            if not text:
                continue
            start_seconds = item.start_seconds + audio_info.timeline_start_seconds
            end_seconds = item.end_seconds + audio_info.timeline_start_seconds
            if not math.isfinite(start_seconds) or not math.isfinite(end_seconds) or start_seconds < 0 or end_seconds < start_seconds:
                raise TranscriptionProviderError("The transcription provider returned invalid timestamps.")
            segments.append(
                TranscriptionSegment(
                    text=text,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    formatted_start_time=format_timestamp(start_seconds),
                    formatted_end_time=format_timestamp(end_seconds),
                    source_filename=safe_filename,
                    source_type=source_type,
                    segment_id=f"transcript-{index}",
                )
            )

        return TranscriptionResult(
            source_filename=safe_filename,
            source_type=source_type,
            status="transcribed" if segments else "no_speech",
            duration_seconds=audio_info.duration_seconds,
            segments=segments,
            document_id=document_id,
            source_id=source_id,
        )
