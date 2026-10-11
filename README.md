# Lumora AI Study Companion

## Backend setup

The FastAPI application is in `backend/app/main.py`. From the repository root, create and activate a virtual environment, then install the root requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the tests from the repository root:

```powershell
python -m pytest -q
```

Start the local API from the repository root:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

The health check is available at `http://localhost:8000/api/health`. Copy `.env.example` to `.env` to customize local settings.

Document extraction endpoints are `POST /api/documents/upload` for PDFs and `POST /api/documents/upload/pptx` for PowerPoint files. PPTX slide numbers are one-based in deck order (the first slide is slide 1); visible slide-number text does not change this source numbering. Extracted images are returned by the processing service with their slide relationship; OCR or vision analysis is not run by basic PPTX parsing.

Lecture media transcription is available at `POST /api/documents/upload/media`. Install FFmpeg and ffprobe, then make both executables available on `PATH` (for example, install FFmpeg from your OS package manager, or add the FFmpeg `bin` directory to `PATH` on Windows). Verify the install with `ffmpeg -version` and `ffprobe -version`; alternatively set `FFMPEG_PATH` and `FFPROBE_PATH` in `.env` to their executable paths.

Set `STT_PROVIDER=whisper_compatible`, `STT_API_URL`, and `STT_MODEL` in `.env` for a Whisper-compatible `/audio/transcriptions` endpoint. Set `STT_API_KEY` only if that endpoint requires authentication. The `.env.example` values are placeholders; do not commit real credentials. Upload, duration, temporary audio size, FFmpeg timeout, and provider timeout are controlled by the `MAX_UPLOAD_SIZE_MB`, `MAX_MEDIA_DURATION_SECONDS`, `MAX_EXTRACTED_AUDIO_SIZE_MB`, `FFMPEG_TIMEOUT_SECONDS`, and `STT_TIMEOUT_SECONDS` settings. Unit tests use mocked provider responses and do not make paid transcription calls. The optional local-media integration test runs only when `LUMORA_RUN_STT_INTEGRATION=1` and `LUMORA_TEST_MEDIA_FILE` are set.

The embedding service accepts an OpenAI-compatible embeddings endpoint. Configure `EMBEDDING_PROVIDER=openai_compatible`, `EMBEDDING_API_URL`, `EMBEDDING_MODEL`, and `EMBEDDING_DIMENSIONS` in `.env`; set `EMBEDDING_API_KEY` locally if your provider requires authentication. For example, the default model is `text-embedding-3-small` with 1536 dimensions. `EMBEDDING_BATCH_SIZE`, `EMBEDDING_TIMEOUT_SECONDS`, and the `EMBEDDING_MAX_RETRIES` / retry delay settings control request behavior. API credentials are read as secret settings and are never included in embedding records. The `mock` provider is available for offline development and tests; its vectors are deterministic test values, not semantic embeddings. No embedding database table or vector column exists yet, so callers should run `validate_vector_collection` before persistence and reindex the collection when changing model or dimension.

RAG retrieval currently uses `InMemoryVectorStore` behind the provider-neutral `VectorStore` interface. It keeps precomputed document vectors in process memory, embeds only the query, and ranks with cosine similarity. The index is nonpersistent and each application worker has its own copy; Supabase/pgvector is not connected yet. Mock embedding results are marked with `is_mock_embedding=true` and must not be interpreted as semantic relevance.

Evidence-grounded answer generation uses the provider interface in `app.services.rag`; the default provider is Gemini through Google's official `google-genai` SDK. Set `ANSWER_PROVIDER=gemini`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL` / `GEMINI_TIMEOUT_SECONDS` in the root `.env`. The default model is `gemini-3.8-flash`. The key is loaded as a secret setting, is not logged, and is never sent to the frontend. If the key is missing, chat returns the existing safe provider-unavailable response. Set `ANSWER_PROVIDER=mock` for offline development; the mock returns insufficient evidence by default and does not demonstrate real model reasoning. `ANSWER_PROVIDER=unconfigured` retains the explicit unavailable provider. Unit tests use a mocked Gemini client and make no network calls.

Unsupported-query handling returns insufficient evidence for empty evidence; the provider policy also treats irrelevant or tangential evidence, inadequate detail, unresolved conflicts, and untraceable answers as insufficient. Retrieval similarity is passed as ranking context only; there is no fixed score threshold because scores are not calibrated across providers or academic subjects. These provider judgments have not been evaluated across subjects and are not a guarantee of reliable unsupported-query detection.
