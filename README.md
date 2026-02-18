<!-- Project logo -->
<p align="center">
  <img src="assets/logo.png" alt="CRA logo" width="160" />
</p>


# CRA — Code Review Agent (FastAPI + React)

A production-quality, modular code review service that combines deterministic static analysis with optional LLM suggestions.

- **Backend**: FastAPI (versioned endpoints under `/v2` and mirrored under `/api/v2` for frontend compatibility)
- **Frontend**: React + Vite + Tailwind
- **Checks**: flake8 + bandit (with a small built-in fallback)
- **Prompt optimization**: context compression + optional ScaleDown compression

---

## On this page

- [Overview](#overview)
- [Features](#features)
- [Supported Languages](#supported-languages)
- [How It Works](#how-it-works)
- [High-Level Architecture](#high-level-architecture)
- [Live Deployment Links](#live-deployment-links)
- [API Quick Start](#api-quick-start)
- [Request Format](#request-format)
- [Response Format](#response-format)
- [Severity Levels](#severity-levels)
- [Error Handling](#error-handling)
- [Configuration & Environment Variables](#configuration--environment-variables)
- [Offline Mode (No LLM)](#offline-mode-no-llm)
- [Limits & Constraints](#limits--constraints)
- [Security & Privacy](#security--privacy)
- [Versioning & Changelog](#versioning--changelog)
- [Contribution Guide](#contribution-guide)

---

## Overview

CRA takes a source file (or raw code), compresses it for efficient prompting, runs static analysis when applicable, and returns a **structured, ranked** set of issues.

You can run CRA in:
- **Offline mode** (no secrets, no network): compression + static analysis only
- **LLM mode**: adds LLM-backed findings via an OpenAI-compatible Chat Completions API

---

## Features

- FastAPI backend with JSON + file upload endpoints
- Ranked, structured issues with category + severity
- Optional strict mode output (fixed-format human-readable findings)
- Optional Firebase token verification (with safe fallback)
- Modern UI (React + Tailwind) and optional Streamlit UI (`ui.py`)

---

## Supported Languages

The UI supports multiple languages for editor highlighting. Static analysis and deeper tooling depend on server runtime availability.

- Python
- JavaScript
- TypeScript
- Java
- C#
- Go
- Rust

---

## How It Works

Pipeline (see `app/ai_agent.py`):

1. **Compress code** (`app/compressor.py`)
2. **Run static analysis** (`app/static_checks.py`)
3. **Build a review prompt** (compressed context + static results)
4. Optionally **compress the prompt** via ScaleDown (`app/scaledown_compression.py`)
5. Call the **LLM** (`app/llm_client.py`) and parse/validate structured JSON
6. **Rank issues** (`app/ranker.py`) and return the response

---

## High-Level Architecture

High-level pipeline overview:

<p align="center">
  <img src="assets/architecture.png" alt="CRA high-level architecture" width="900" />
</p>

---

## Live Deployment Links

- Frontend (Vercel): https://coderagent.vercel.app/
- Backend (Render): https://code-review-agent-api.onrender.com/

> Tip: If you call the API from a browser, the backend must allow your frontend origin via `CODE_REVIEW_CORS_ORIGINS` (example: `https://coderagent.vercel.app`).

---

## API Quick Start

### Health check

```bash
curl https://code-review-agent-api.onrender.com/healthz
```

### Review code (v2 JSON)

```bash
curl -X POST https://code-review-agent-api.onrender.com/v2/review/file \
  -H "Content-Type: application/json" \
  -d '{"filename":"input.py","code":"def add(a,b):\n    return a+b\n","language":"python","enabled_checks":{"security":true,"style":true,"performance":true}}'
```

> Note: Versioned routes are under `/v2/...` and mirrored under `/api/v2/...` for frontend compatibility.

---

## Request Format

Recommended endpoint used by the frontend:

- `POST /v2/review/file`

Example JSON payload:

```json
{
  "filename": "input.py",
  "code": "def add(a, b):\n    return a + b\n",
  "language": "python",
  "enabled_checks": {
    "security": true,
    "style": true,
    "performance": true
  }
}
```

---

## Response Format

High-level response includes:

- `issues[]` — ranked findings
- `score` — normalized score + counts
- `static_analysis` — tool output summaries

Example (trimmed):

```json
{
  "issues": [
    {
      "file": "input.py",
      "line": 12,
      "category": "security",
      "severity": "high",
      "description": "User-controlled input is used in SQL query",
      "suggestion": "Use parameterized queries / prepared statements",
      "source": "bandit"
    }
  ],
  "score": {
    "score": 92,
    "counts_by_severity": { "critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0 }
  },
  "static_analysis": {
    "flake8": { "issues": [] },
    "bandit": { "result": { "results": [] } }
  }
}
```

---

## Severity Levels

Severities are normalized to:

- `critical`
- `high`
- `medium`
- `low`
- `info`

---

## Error Handling

- `400` — invalid input (missing code, invalid URL, etc.)
- `422` — validation error from request parsing
- `502` — upstream issues (LLM provider/network/runtime errors)

---

## Configuration & Environment Variables

### Frontend

- `VITE_API_BASE_URL` — point the UI at your backend
  - Example: `https://code-review-agent-api.onrender.com`

### Backend

CORS:
- `CODE_REVIEW_CORS_ORIGINS` — comma-separated browser origins
  - Example: `https://coderagent.vercel.app`
- `CODE_REVIEW_CORS_ORIGIN_REGEX` — optional regex (useful for Vercel previews)

LLM:
- `LLM_PROVIDER` — defaults to `openai`; set `none` for offline mode
- `LLM_API_KEY`
- `LLM_BASE_URL` (default: `https://openrouter.ai/api/v1`)
- `LLM_MODEL` (default: `qwen/qwen3-coder:free`)
- `LLM_TIMEOUT_SECONDS` — request timeout (default: 30)

ScaleDown (optional):
- `SCALEDOWN_API_KEY`

---

## Offline Mode (No LLM)

Set:
- `LLM_PROVIDER=none`

Result:
- No network calls
- Deterministic runs
- Static analysis still executes

---

## Limits & Constraints

- Large files may be compressed/truncated to fit prompt limits.
- Some language-specific checks depend on runtime availability.
- In offline mode, LLM-backed findings are disabled.

---

## Security & Privacy

- Do not commit real API keys.
- Do not commit `.env` or Firebase Admin SDK service account JSON.
- `/configz` never returns secret values.

---

## Versioning & Changelog

- API routes are versioned under `/v2`.
- The app version is exposed via `GET /healthz` (`version` field).

---

## Contribution Guide

1. Fork the repo and create a feature branch.
2. Run backend tests (`pytest`) and frontend build checks.
3. Open a PR describing the change and validation steps.

---

## Local development (Windows / cmd.exe)

### 0) Offline mode (no network, no secrets)

```cmd
set LLM_PROVIDER=none
```

### 1) Create a virtualenv + install dependencies

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Run the API

```cmd
uvicorn app.main:app --reload
```

### 3) Run the UI

Start everything:

```cmd
start_app.bat
```

Or run Streamlit:

```cmd
streamlit run ui.py
```

---

## Tests

Backend tests:

```cmd
pytest
```

Interactive test runner:

```cmd
run_tests.bat
```

---


## Quality gates (optional but recommended)

```cmd
ruff check .
ruff format .
pyright
```
