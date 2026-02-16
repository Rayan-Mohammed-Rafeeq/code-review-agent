<!-- Project logo -->
<p align="center">
  <img src="assets/logo.png" alt="Code Review Agent logo" width="160" />
</p>

# Code Review Agent (FastAPI)

> If you have a deployed UI/API, add the URLs here. Otherwise, keep this repo runnable locally.

A production-quality, modular AI-powered code review service that combines:
- **Static analysis** (flake8 + bandit, with a small built-in fallback)
- **Context compression** for shorter / cheaper prompts
- **LLM-backed review** (OpenAI-compatible Chat Completions)
- **Optional prompt compression via ScaleDown** (compression only; not an LLM)
- **Optional Streamlit UI** for interactive reviews

---

## Before you push to GitHub (quick safety checklist)

- Do **not** commit `.env` or any Firebase service account JSON.
- Use `.env.example` as the template for local development.
- For judge/evaluator runs with no secrets, use **offline mode**: `LLM_PROVIDER=none`.
- `start_app.bat` is path-independent and should work from any folder.

---

## What you get

- FastAPI backend with endpoints:
  - `POST /review` (JSON)
  - `POST /review/file` (multipart upload)
  - `GET /healthz` (liveness)
  - `GET /configz` (sanitized config)
- Structured response with:
  - `compressed_context`
  - `static_analysis` (flake8 + bandit outputs)
  - `issues` (ranked, structured findings)
  - optional `strict_findings` (human-readable fixed format)

---

## Quick start (Windows / cmd.exe)

### 0) Judge-friendly default: offline mode (no network, no secrets)

If you're running this for evaluation without any external credentials, set:
- `LLM_PROVIDER=none`

In this mode the API still performs **compression + static analysis**, and returns an empty `issues[]` list (deterministic, no network calls).

### 1) Create a virtualenv + install dependencies

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure the LLM (optional)

If you want LLM-backed reviews, configure these environment variables (or create a `.env` file in the repo root):
- `LLM_API_KEY`
- `LLM_BASE_URL` (example: `https://api.openai.com/v1`)
- `LLM_MODEL` (example: `gpt-4o-mini`)

Security note:
- Never commit `.env` or Firebase service-account JSON keys. Use `.env.example` as a template.

### 3) Run the API

```cmd
uvicorn app.main:app --reload
```

Open:
- API health: `http://127.0.0.1:8000/healthz`
- Swagger UI: `http://127.0.0.1:8000/docs`

---

## Run the UI (Streamlit)

The repo includes a Streamlit frontend in `ui.py`.

### Auth in the UI

Auth is disabled in the UI.

If your API requires authentication, call it directly (e.g., via curl/Postman) or put the Streamlit app behind your own auth layer.

### Option A: Start everything with the provided script

```cmd
start_app.bat
```

This opens two windows:
- Backend (FastAPI) on `http://127.0.0.1:8000`
- Frontend (Streamlit) on `http://localhost:8501`

### Option B: Start UI manually

If you already started the backend:

```cmd
streamlit run ui.py
```

If your API isnt at `http://127.0.0.1:8000`, set:
- `CODE_REVIEW_API_URL` (used by the UI)

---

## Deployment environment variables

### Streamlit UI

- `CODE_REVIEW_API_URL`  base URL of your deployed API
  - Example: `https://my-code-review-api.onrender.com`

### FastAPI backend

- `CODE_REVIEW_CORS_ORIGINS`  comma-separated list of allowed browser origins
  - Example: `https://my-ui.example.com`
  - Example (multiple): `https://my-ui.example.com,https://my-ui2.example.com`


- `LLM_PROVIDER`  defaults to `openai`
  - Set `LLM_PROVIDER=none` to **disable LLM calls** (offline mode)
- `LLM_TIMEOUT_SECONDS`  request timeout (default: 30)
- `SCALEDOWN_API_KEY`  enables ScaleDown prompt compression (optional)

### Offline mode (no network / no LLM)

If you want to use only compression + static analysis:
- Set `LLM_PROVIDER=none`

The API will return an empty `issues` list. Static analysis still runs.

---

## API

### `POST /review` (JSON)

Request body:

```json
{
  "code": "def add(a, b):\n    return a + b\n",
  "language": "python",
  "filename": "example.py",
  "strict": false
}
```

Notes:
- Only `python` is supported end-to-end right now.
- If `strict=true`, the response also includes `strict_findings`.

### `POST /review/file` (multipart)

Upload a UTF-8 Python file using `multipart/form-data` with the field name `file`.

### Response shape

High-level response fields:
- `compressed_context`  compressed code summary
- `static_analysis`  tool outputs:
  - `static_analysis.flake8.issues[]`
  - `static_analysis.bandit.result.results[]`
- `issues[]`  structured items:
  - `severity`: `high | medium | low`
  - `category`: `security | bug | performance | style`
  - `description`, `suggestion`
  - optional `location`

### Health + config

- `GET /healthz` returns `{ ok, service, version }`
- `GET /configz` returns sanitized config (never returns the API key value)

---

## How it works (high level)

The backends review pipeline (see `app/ai_agent.py`):
1. **Compress code** (`app/compressor.py`)
2. **Run static analysis** (`app/static_checks.py`)
3. **Build a review prompt** that includes compressed context + static results
4. Optionally **compress the prompt** via ScaleDown (`app/scaledown_compression.py`)
5. Call the **real LLM** (`app/llm_client.py`) and parse/validate structured JSON
6. **Rank issues** (`app/ranker.py`) and return the response

---

## Tests

Run all tests:

```cmd
pytest
```

Theres also an interactive menu script:

```cmd
run_tests.bat
```

---

## Troubleshooting

### 400: LLM is not configured (missing: )

Set `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`, then restart the API.

If you intended to run without an LLM, set:
- `LLM_PROVIDER=none`

### 401 / 404 / 400 from the provider

The LLM client is built for OpenAI-compatible Chat Completions endpoints.
Common causes:
- `LLM_BASE_URL` missing `/v1`
- wrong `LLM_MODEL`
- key copied with quotes or redacted characters

### flake8/bandit not producing output

`flake8` and `bandit` are invoked via `python -m ...`. If the tools fail,
responses include `tool_error` / `stderr` to help diagnose environment issues.

---

## Project structure

- `app/main.py`  FastAPI app and endpoints
- `app/ai_agent.py`  orchestrates compression + static checks + LLM review
- `app/llm_client.py`  OpenAI-compatible client + safe JSON parsing
- `app/static_checks.py`  flake8 + bandit runner with small builtin fallback
- `app/compressor.py`  Python code compression
- `app/scaledown_compression.py`  optional ScaleDown prompt compression
- `ui.py`  Streamlit frontend
- `tests/`  pytest suite

---

## Security notes

- Never commit real API keys.
- Prefer using a local `.env` file for development.
- The `/configz` endpoint intentionally never returns your key.

## Firebase Auth (optional)

The backend can verify Firebase ID tokens if you provide a Firebase **Admin SDK service account**.

### Backend credentials discovery

The backend looks for credentials in this order:

1. `FIREBASE_SERVICE_ACCOUNT_JSON`  an env var containing the full service account JSON
2. `FIREBASE_SERVICE_ACCOUNT_FILE`  a path to a JSON file
3. A file named `firebase-service-account.json` in the repo root (current working directory)

If none are provided (or initialization fails), the backend falls back to the built-in demo auth.

### Troubleshooting: `CONFIGURATION_NOT_FOUND`

This error is almost always a **project mismatch**:

- Your frontend is generating an ID token for Firebase project **A**
- Your backend service account JSON belongs to project **B**

To debug locally:

- Visit `GET /configz` and check `firebase.credential_source` and `firebase.initialized`.
- Call `GET /auth/firebase_debug` with your `Authorization: Bearer <id_token>` header.
  It returns **unverified** token hints like `iss` and the inferred `firebase_project_id`.

Fix is to ensure the tokens project (from `iss`) matches the service account JSON `project_id`.

## Quality gates (optional but recommended)

This repo includes lightweight tooling to show real engineering beyond raw LLM output:
- Lint: `ruff check .`
- Format: `ruff format .`
- Types: `pyright`
