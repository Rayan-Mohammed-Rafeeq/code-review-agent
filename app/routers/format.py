from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from app.formatters import FormatterUnavailableError, format_code

router = APIRouter(prefix="/v2/format", tags=["format"])


class FormatRequest(BaseModel):
    code: str = Field(..., description="Raw code to format")
    language: str | None = Field(default=None, description="Language identifier (python, javascript, java, ...)")
    filename: str | None = Field(default=None, description="Optional filename used for formatter inference")


class FormatResponse(BaseModel):
    code: str
    formatter: str
    changed: bool


@router.post("", response_model=FormatResponse)
async def format_endpoint(payload: FormatRequest = Body(...)) -> FormatResponse:
    try:
        result = format_code(code=payload.code, language=payload.language, filename=payload.filename)
        return FormatResponse(code=result.formatted_code, formatter=result.formatter, changed=result.changed)
    except FormatterUnavailableError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Keep the message short to avoid leaking execution context.
        raise HTTPException(status_code=502, detail=f"Formatter failed: {type(e).__name__}")
