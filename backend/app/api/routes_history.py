"""Analysis-history endpoints."""
from __future__ import annotations

import shutil

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..config import (FEATURE_VERSION, MODEL_NAME, MODEL_VERSION,
                      PIPELINE_VERSION, REPO_ROOT)
from ..core.exceptions import NotFoundError
from ..core.timeutil import iso_utc
from ..db import repository
from ..db.models import Analysis
from ..dependencies import get_db
from ..schemas.history import AnalysisDetail, HistoryItem, HistoryList

router = APIRouter(prefix="/api/v1", tags=["history"])


def _url(path: str | None) -> str | None:
    return f"/{path}" if path else None


@router.get("/analyses", response_model=HistoryList)
def list_analyses(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    label: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
) -> HistoryList:
    rows, total = repository.list_analyses(
        db, limit=limit, offset=offset, label=label, search=search, sort=sort, order=order)
    items = [
        HistoryItem(
            id=r.id, created_at=iso_utc(r.created_at), filename=r.filename,
            quality_score=r.quality_score, quality_label=r.quality_label,
            quality_class=r.quality_class, overall_confidence=r.overall_confidence,
            review_recommended=bool(r.review_recommended), primary_issue=r.primary_issue,
            thumbnail_url=_url(r.thumbnail_path),
        )
        for r in rows
    ]
    return HistoryList(items=items, total=total, limit=limit, offset=offset)


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisDetail:
    r: Analysis | None = repository.get(db, analysis_id)
    if r is None:
        raise NotFoundError(f"Analysis {analysis_id} not found.")
    return AnalysisDetail(
        id=r.id, created_at=iso_utc(r.created_at), filename=r.filename, format=r.format,
        image={"width": r.width, "height": r.height, "channels": r.channels,
               "file_size_kb": round(r.file_size_bytes / 1024, 1)},
        quality_score=r.quality_score, quality_label=r.quality_label,
        quality_class=r.quality_class, overall_confidence=r.overall_confidence,
        review_recommended=bool(r.review_recommended), primary_issue=r.primary_issue,
        detected_issues=r.detected_issues, issues=r.issues, statistics=r.statistics,
        dimensions=r.dimensions, signal_agreement=r.signal_agreement, anomaly=r.anomaly,
        forensics=r.forensics, narrative=r.narrative,
        thumbnail_url=_url(r.thumbnail_path), heatmap_url=_url(r.heatmap_path),
        problem_regions_url=_url(r.problem_regions_path),
        model_info={"model_name": MODEL_NAME, "model_version": MODEL_VERSION,
                    "feature_version": FEATURE_VERSION, "pipeline_version": PIPELINE_VERSION},
        analysis_time_ms=r.analysis_time_ms,
    )


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, db: Session = Depends(get_db)) -> Response:
    if not repository.delete(db, analysis_id):
        raise NotFoundError(f"Analysis {analysis_id} not found.")
    media_dir = REPO_ROOT / "media" / analysis_id
    if media_dir.exists():
        shutil.rmtree(media_dir, ignore_errors=True)
    return Response(status_code=204)
