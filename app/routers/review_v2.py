from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from app.analysis.models import FileReviewRequest, ProjectReviewRequest, ProjectReviewResult, ReviewResult
from app.analysis.pipeline import ReviewPipeline
from app.deps import get_pipeline

router = APIRouter(prefix="/v2/review", tags=["review-v2"])


@router.post("/file", response_model=ReviewResult)
async def review_file_v2(
    payload: FileReviewRequest = Body(...),
    strict: bool = False,
    pipeline: ReviewPipeline = Depends(get_pipeline),
) -> ReviewResult:
    try:
        return await pipeline.review_file(
            filename=payload.filename,
            code=payload.code,
            strict=bool(strict),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/project", response_model=ProjectReviewResult)
async def review_project_v2(
    payload: ProjectReviewRequest = Body(...),
    pipeline: ReviewPipeline = Depends(get_pipeline),
) -> ProjectReviewResult:
    try:
        return await pipeline.review_project(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
