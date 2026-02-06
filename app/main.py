from __future__ import annotations

import logging
import os

from fastapi import Body, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.ai_agent import CodeReviewAgent
from app import deps
from app.deps import get_agent
from app.logging_config import configure_logging
from app.models import ReviewRequest, ReviewResponse
from app.strict_format import format_strict_findings
from app.settings import Settings

configure_logging()

logger = logging.getLogger("code_review_agent")

APP_VERSION = "1.0.0"

app = FastAPI(title="Code Review Agent", version=APP_VERSION)

# --- CORS (for Streamlit UI / browser clients) ---
# In local dev, UI and API often run on different ports (8501 vs 8000).
# In deployment, they are almost always different origins.
#
# Configure allowed origins via CODE_REVIEW_CORS_ORIGINS.
# Examples:
#   CODE_REVIEW_CORS_ORIGINS=https://code-review-agent.streamlit.app
#   CODE_REVIEW_CORS_ORIGINS=https://my-ui.example.com,https://my-ui2.example.com
_cors_origins_raw = (os.getenv("CODE_REVIEW_CORS_ORIGINS") or "").strip()
if _cors_origins_raw:
    cors_origins = [o.strip().rstrip("/") for o in _cors_origins_raw.split(",") if o.strip()]
else:
    # Safe-ish default for local dev.
    cors_origins = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost",
        "http://127.0.0.1",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Validate configuration and connectivity on startup."""
    settings = deps.get_settings_dep()

    # ScaleDown is not an LLM provider. LLM_PROVIDER only selects the real LLM backend.
    provider = (settings.llm_provider or "openai").lower().strip()
    logger.info(f"Starting with LLM_PROVIDER={provider}")


def _ensure_llm_configured(s=None) -> None:
    """Raise a 400 with guidance when the app isn't configured to call an LLM.

    The backend supports LLM_PROVIDER=none for offline mode (it will return an
    empty issues list). For any other provider, we require key/base_url/model.
    """
    # NOTE: This function intentionally uses the injected Settings object when
    # available. If it's not provided, fall back to deps.get_settings() (which
    # tests can monkeypatch).
    if s is None:
        s = deps.get_settings_dep()
    provider = (s.llm_provider or "openai").lower().strip()
    if provider == "none":
        return

    # Always require a key when provider isn't 'none'. Even if a Settings default
    # provides base_url/model, a missing key means the backend can't authenticate.
    missing: list[str] = []
    if not (s.llm_api_key or "").strip():
        missing.append("LLM_API_KEY")

    # base_url/model are required for OpenAI-compatible clients.
    if not (s.llm_base_url or "").strip():
        missing.append("LLM_BASE_URL")
    if not (s.llm_model or "").strip():
        missing.append("LLM_MODEL")

    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "LLM is not configured (missing: "
                + ", ".join(missing)
                + "). Set these environment variables and restart the API, or set LLM_PROVIDER=none to run without LLM calls."
            ),
        )


@app.post("/review", response_model=ReviewResponse)
async def review_json_endpoint(
    payload: ReviewRequest = Body(...),
    agent: CodeReviewAgent = Depends(get_agent),
    settings: Settings = Depends(deps.get_settings_dep),
):
    """JSON-only review endpoint.

    Accepts:
      {"code": "...", "language": "python", "filename": "optional.py"}

    If `strict=true`, the response also includes `strict_findings`, a human-readable
    findings string in a fixed format.
    """
    # Basic guardrail: we only support python end-to-end right now.
    if payload.language != "python":
        raise HTTPException(status_code=400, detail="Only 'python' is supported right now")

    # Pass settings explicitly so tests can monkeypatch app.main.get_settings
    # and have it deterministically reflected here.
    _ensure_llm_configured(settings)

    try:
        compressed, static_dict, issues = await agent.review(
            code=payload.code,
            filename=payload.filename or "input.py",
            language=payload.language,
            strict=bool(payload.strict),
        )
    except RuntimeError as e:
        logger.warning("Review failed due to runtime error", extra={"source_filename": payload.filename})
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during review", extra={"source_filename": payload.filename})
        # Surface a small, safe error message for debuggability.
        raise HTTPException(status_code=502, detail=f"Review failed: {type(e).__name__}: {e}")

    strict_findings = format_strict_findings(issues) if payload.strict else None
    return ReviewResponse(
        compressed_context=compressed,
        static_analysis=static_dict,
        issues=issues,
        strict_findings=strict_findings,
    )


@app.post("/review/file", response_model=ReviewResponse)
async def review_file_endpoint(
    file: UploadFile = File(...),
    agent: CodeReviewAgent = Depends(get_agent),
    settings: Settings = Depends(deps.get_settings_dep),
):
    """Multipart file-upload review endpoint."""
    try:
        code, filename = await _read_code_from_file(file=file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _ensure_llm_configured(settings)

    try:
        compressed, static_dict, issues = await agent.review(code=code, filename=filename, language="python")
    except RuntimeError as e:
        logger.warning("Review failed due to runtime error", extra={"source_filename": filename})
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during review", extra={"source_filename": filename})
        raise HTTPException(status_code=502, detail=f"Review failed: {type(e).__name__}: {e}")

    return ReviewResponse(compressed_context=compressed, static_analysis=static_dict, issues=issues)


async def _read_code_from_file(*, file: UploadFile) -> tuple[str, str]:
    raw = await file.read()
    try:
        code = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("Uploaded file must be UTF-8 encoded") from e
    filename = file.filename or "input.py"
    if not filename.endswith(".py"):
        filename = filename + ".py"
    return code, filename


# Backwards-compatible helper kept for internal use only.
async def _read_code(*, payload: ReviewRequest | None, file: UploadFile | None) -> tuple[str, str]:
    if file is not None:
        return await _read_code_from_file(file=file)

    if payload is None:
        raise ValueError("Provide either JSON body with 'code' or upload a file")

    return payload.code, payload.filename or "input.py"


@app.get("/healthz")
def healthz():
    return JSONResponse({"ok": True, "service": "code-review-agent", "version": APP_VERSION})


@app.get("/configz")
def configz():
    # Never return the key itself.
    llm_key_set = bool(os.getenv("LLM_API_KEY"))
    return JSONResponse(
        {
            "llm_api_key_set": llm_key_set,
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "llm_model": os.getenv("LLM_MODEL"),
        }
    )
