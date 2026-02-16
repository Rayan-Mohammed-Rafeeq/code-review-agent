from __future__ import annotations

import logging
import os
import re
import urllib.parse

import requests
from fastapi import Body, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app import deps, firebase_auth
from app.ai_agent import CodeReviewAgent
from app.deps import get_agent
from app.firebase_debug import get_token_hints
from app.logging_config import configure_logging
from app.models import ReviewRequest, ReviewResponse
from app.routers.review_v2 import router as review_v2_router
from app.settings import Settings
from app.strict_format import format_strict_findings

configure_logging()

logger = logging.getLogger("code_review_agent")

APP_VERSION = "1.0.0"

app = FastAPI(title="Code Review Agent", version=APP_VERSION)
app.include_router(review_v2_router)


def _normalize_github_repo_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        raise ValueError("GitHub repo URL is required")

    parsed = urllib.parse.urlparse(u)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("GitHub repo URL must start with http(s)")

    host = (parsed.netloc or "").lower()
    if host not in ("github.com", "www.github.com"):
        raise ValueError("Only github.com URLs are supported")

    path = (parsed.path or "").strip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("GitHub repo URL must look like https://github.com/<owner>/<repo>")

    owner, repo = parts[0], parts[1]
    repo = re.sub(r"\.git$", "", repo, flags=re.IGNORECASE)
    return f"https://github.com/{owner}/{repo}"


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
    #
    # IMPORTANT: only enforce LLM configuration when a real LLM provider is enabled.
    # In offline mode (LLM_PROVIDER=none) the LLM client returns an empty issues list.
    if (settings.llm_provider or "openai").lower().strip() != "none":
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
    resp_model = ReviewResponse(
        compressed_context=compressed,
        static_analysis=static_dict,
        issues=issues,
        strict_findings=strict_findings,
    )

    out = resp_model.model_dump()
    return JSONResponse(out)


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

    # Pass settings explicitly so tests can monkeypatch app.main.get_settings
    # and have it deterministically reflected here.
    if (settings.llm_provider or "openai").lower().strip() != "none":
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

    resp_model = ReviewResponse(compressed_context=compressed, static_analysis=static_dict, issues=issues)

    out = resp_model.model_dump()
    return JSONResponse(out)


@app.post("/review/github", response_model=ReviewResponse)
async def review_github_endpoint(
    payload: dict = Body(...),
    agent: CodeReviewAgent = Depends(get_agent),
    settings: Settings = Depends(deps.get_settings_dep),
):
    """Review a GitHub repo by fetching a single file from it.

    Accepts:
      {"repo_url": "https://github.com/owner/repo", "path": "path/in/repo.py", "ref": "main", "strict": false}

    Note: This uses the unauthenticated raw GitHub endpoint. Large/complex repos
    are intentionally out-of-scope for now.
    """
    repo_url = _normalize_github_repo_url(payload.get("repo_url") or "")
    path = (payload.get("path") or "").strip() or "README.md"
    ref = (payload.get("ref") or "").strip() or "main"
    strict = bool(payload.get("strict") or False)

    if not path.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are supported")

    parsed = urllib.parse.urlparse(repo_url)
    owner, repo = [p for p in parsed.path.strip("/").split("/") if p][:2]
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"

    # This endpoint requires network access. Keep it deterministic for judges:
    # if offline mode is enabled, fail fast with a clear message.
    if (settings.llm_provider or "openai").lower().strip() == "none":
        raise HTTPException(status_code=400, detail="GitHub review is disabled in offline mode (LLM_PROVIDER=none)")

    _ensure_llm_configured(settings)

    try:
        r = requests.get(raw_url, timeout=15)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch GitHub raw file: {e.__class__.__name__}")

    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to fetch file from GitHub (HTTP {r.status_code})")

    code = r.text
    filename = os.path.basename(path) or "input.py"

    try:
        compressed, static_dict, issues = await agent.review(
            code=code, filename=filename, language="python", strict=strict
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    resp_model = ReviewResponse(
        compressed_context=compressed,
        static_analysis=static_dict,
        issues=issues,
        strict_findings=(format_strict_findings(issues) if strict else None),
    )

    out = resp_model.model_dump()
    return JSONResponse(out)


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
    # Avoid secrets: only report whether Firebase verification is configured and initialized.
    fb_configured = bool(
        os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        or os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
        or os.path.exists(os.path.join(os.getcwd(), "firebase-service-account.json"))
    )
    fb_initialized = bool(firebase_auth._init_admin())  # type: ignore[attr-defined]
    return JSONResponse(
        {
            "ok": True,
            "service": "code-review-agent",
            "version": APP_VERSION,
            "firebase_configured": fb_configured,
            "firebase_initialized": fb_initialized,
        }
    )


@app.get("/configz")
def configz():
    # Never return the key itself.
    llm_key_set = bool(os.getenv("LLM_API_KEY"))
    fb_source = firebase_auth._cred_source()  # type: ignore[attr-defined]
    fb_initialized = bool(firebase_auth._init_admin())  # type: ignore[attr-defined]
    return JSONResponse(
        {
            "llm_api_key_set": llm_key_set,
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "llm_model": os.getenv("LLM_MODEL"),
            "firebase": {
                "credential_source": fb_source,
                "initialized": fb_initialized,
            },
        }
    )


@app.get("/auth/firebase_debug")
def firebase_debug(authorization: str | None = Header(default=None)):
    """Debug endpoint to diagnose Firebase token/project mismatches.

    Returns *unverified* JWT payload hints (aud/iss/project) and backend Firebase init status.
    This is intended for local debugging. Do not rely on it for security decisions.

    Note: this *does not* authenticate anyone. It's a diagnostics endpoint only.
    """
    token = None
    if authorization and str(authorization).lower().startswith("bearer "):
        token = str(authorization).split(" ", 1)[1].strip() or None

    hints = get_token_hints(token or "") if token else None

    return JSONResponse(
        {
            "firebase": {
                "credential_source": firebase_auth._cred_source(),  # type: ignore[attr-defined]
                "initialized": bool(firebase_auth._init_admin()),  # type: ignore[attr-defined]
            },
            "token_hints": (hints.__dict__ if hints else None),
        }
    )


def _ensure_llm_configured(s=None) -> None:
    """Raise a 400 with guidance when the app isn't configured to call an LLM.

    The backend supports LLM_PROVIDER=none for offline mode (it will return an
    empty issues list). For any other provider, we require key/base_url/model.
    """
    if s is None:
        s = deps.get_settings_dep()
    provider = (s.llm_provider or "openai").lower().strip()
    if provider == "none":
        return

    missing: list[str] = []
    if not (s.llm_api_key or "").strip():
        missing.append("LLM_API_KEY")
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
