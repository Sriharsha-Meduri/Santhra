"""Analysis endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import (ISSUE_TYPES, MODEL_INPUT_SIZE, MODEL_NAME, MODEL_VERSION,
                      QUALITY_CLASSES, get_settings)
from ..core.exceptions import (FileTooLargeError, InvalidImageError,
                               SanthraError)
from ..db import repository
from ..dependencies import get_db, request_id
from ..schemas.analysis import AnalysisResponse
from ..services.analysis_service import analyze_image
from ..services.inference_service import get_engine

router = APIRouter(prefix="/api/v1", tags=["analysis"])


async def _read_limited(file: UploadFile) -> bytes:
    settings = get_settings()
    data = await file.read(settings.max_upload_size_bytes + 1)
    if len(data) > settings.max_upload_size_bytes:
        raise FileTooLargeError(
            f"File exceeds {settings.max_upload_size_mb} MB limit.")
    if not data:
        raise InvalidImageError("Empty upload.")
    return data


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    rid: str = Depends(request_id),
) -> AnalysisResponse:
    data = await _read_limited(file)
    # Offload the CPU-heavy pipeline (torch inference + Grad-CAM + OpenCV) to a
    # worker thread so it does not block the event loop for other requests.
    response, record = await run_in_threadpool(
        analyze_image, data, file.filename, request_id=rid)
    repository.create(db, record)
    return response


@router.post("/analyze/batch", tags=["analysis"])
async def analyze_batch(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    rid: str = Depends(request_id),
) -> dict:
    results, scores = [], []
    counts = {c: 0 for c in QUALITY_CLASSES}
    for f in files[:25]:
        try:
            data = await _read_limited(f)
            response, record = await run_in_threadpool(
                analyze_image, data, f.filename, request_id=rid)
            repository.create(db, record)
            counts[response["quality_class"]] += 1
            scores.append(response["quality_score"])
            results.append({
                "id": response["id"], "filename": response["filename"],
                "quality_score": response["quality_score"],
                "quality_label": response["quality_label"],
                "detected_issue_types": response["detected_issue_types"],
                "review_recommended": response["review_recommended"],
            })
        except SanthraError as exc:  # expected, user-facing validation errors
            results.append({"filename": f.filename, "error": exc.message})
        except Exception:  # unexpected: do not leak internals, do not abort batch
            results.append({"filename": f.filename, "error": "Analysis failed."})
    return {
        "total": len(files),
        "analysed": len(scores),
        "failed": len(files) - len(scores),
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "class_counts": counts,
        "results": results,
    }


@router.get("/model/info", tags=["model"])
def model_info() -> dict:
    engine = get_engine()
    meta = engine.meta
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "input_resolution": MODEL_INPUT_SIZE,
        "quality_classes": QUALITY_CLASSES,
        "issue_types": ISSUE_TYPES,
        "framework": meta.get("framework", "pytorch"),
        "pretrained_backbone": meta.get("pretrained_backbone", True),
        "loss_weights": meta.get("loss_weights", {}),
        "trained_at": meta.get("trained_at"),
        "validation_metrics": meta.get("val_metrics", {}),
        "device": engine.device,
        "model_loaded": engine.model_loaded,
        "anomaly_model_loaded": engine.anomaly_loaded,
        "calibrated": bool(engine.calibrator.issue_temperatures),
    }


@router.get("/statistics", tags=["analysis"])
def statistics(db: Session = Depends(get_db)) -> dict:
    return repository.statistics(db)
