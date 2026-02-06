# Code Review Agent (FastAPI)

A production-quality, modular AI-powered code review service:
- Accepts Python source as raw text or uploaded file
- Compresses code context (names, signatures, control flow) while stripping comments/docstrings
- Runs static checks (flake8 + bandit) *before* AI review
- Sends compressed context + static results to an LLM
- Returns structured, ranked JSON feedback

## Quick start

Create and activate a virtualenv, then install deps:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run the API:

```cmd
uvicorn app.main:app --reload
```

Then POST to `http://127.0.0.1:8000/review`.

### Example (JSON body)

```json
{
  "code": "def add(a,b):\n    return a+b\n"
}
```

### Example (file upload)

Use `multipart/form-data` with `file` and optional `filename`.

## Configuration

Set the LLM API key via environment variable:

- `LLM_API_KEY` (required)
- `LLM_BASE_URL` (optional, default: OpenAI compatible URL)
- `LLM_MODEL` (optional)

Never hardcode API keys in source control.

## Tests

```cmd
pytest -q
```

