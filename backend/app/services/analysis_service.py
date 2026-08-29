"""End-to-end analysis orchestration."""
from __future__ import annotations

import base64
import hashlib
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from ..config import (APP_VERSION, FEATURE_VERSION, MODEL_NAME, MODEL_VERSION,
                      PIPELINE_VERSION, REPO_ROOT)
from ..core.logging import get_logger, log_context
from ..core.security import decode_image, sanitize_filename
from ..core.timeutil import iso_utc
from .explainability_service import build_explainability
from .feature_service import build_statistics, extract_features
from .fusion_service import fuse
from .inference_service import get_engine

logger = get_logger("santhra.analysis")
MEDIA_DIR = REPO_ROOT / "media"


def _save_png(rgb: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def _save_dataurl(dataurl: str | None, path: Path) -> str | None:
    if not dataurl or not dataurl.startswith("data:image"):
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(dataurl.split(",", 1)[1]))
    return f"media/{path.parent.name}/{path.name}"


def analyze_image(data: bytes, filename: str | None, request_id: str = "-") -> tuple[dict, dict]:
    """Run the full pipeline. Returns (api_response, db_record)."""
    t0 = time.perf_counter()
    rgb, fmt = decode_image(data)                    # validates + decodes
    analysis_id = uuid.uuid4().hex
    image_hash = hashlib.sha256(data).hexdigest()
    h, w = rgb.shape[:2]

    features = extract_features(rgb, len(data))
    engine = get_engine()
    ml = engine.predict(rgb)
    anomaly = engine.anomaly(rgb)
    fusion = fuse(ml, features, anomaly)
    statistics = build_statistics(rgb, features, len(data))
    explain = build_explainability(rgb, features, fusion, anomaly, engine)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    # persist media on disk (never in the DB)
    media = MEDIA_DIR / analysis_id
    thumb = rgb
    scale = 320 / max(h, w)
    if scale < 1:
        thumb = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    _save_png(thumb, media / "thumb.png")
    thumb_path = f"media/{analysis_id}/thumb.png"
    heatmap_path = _save_dataurl(explain["heatmap"], media / "heatmap.png")
    problem_path = _save_dataurl(explain["problem_regions"], media / "problem.png")

    created = datetime.now(timezone.utc)
    model_info = {
        "model_name": MODEL_NAME, "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION, "pipeline_version": PIPELINE_VERSION,
        "app_version": APP_VERSION, "model_score": fusion["model_score"],
        "cv_score": fusion["cv_score"], "device": engine.device,
    }

    response = {
        "id": analysis_id,
        "created_at": iso_utc(created),
        "filename": sanitize_filename(filename),
        "format": fmt,
        "image": {
            "width": w, "height": h, "channels": int(rgb.shape[2]),
            "megapixels": round(w * h / 1e6, 3),
            "aspect_ratio": round(w / h, 3),
            "file_size_kb": round(len(data) / 1024, 1),
        },
        "quality_score": fusion["quality_score"],
        "quality_label": fusion["quality_label"],
        "quality_class": fusion["quality_class"],
        "class_probabilities": fusion["class_probabilities"],
        "overall_confidence": fusion["overall_confidence"],
        "overall_confidence_value": fusion["overall_confidence_value"],
        "review_recommended": fusion["review_recommended"],
        "review_reasons": fusion["review_reasons"],
        "issues": fusion["issues"],
        "detected_issue_types": fusion["detected_issue_types"],
        "dimensions": fusion["dimensions"],
        "statistics": statistics,
        "signal_agreement": fusion["signal_agreement"],
        "anomaly": fusion["anomaly"],
        "integrity": fusion["integrity"],
        "explainability": explain,
        "model_info": model_info,
        "analysis_time_ms": elapsed_ms,
    }

    db_record = {
        "id": analysis_id, "created_at": created,
        "filename": response["filename"], "image_hash": image_hash, "format": fmt,
        "width": w, "height": h, "channels": int(rgb.shape[2]), "file_size_bytes": len(data),
        "quality_score": fusion["quality_score"], "quality_label": fusion["quality_label"],
        "quality_class": fusion["quality_class"], "overall_confidence": fusion["overall_confidence"],
        "review_recommended": int(fusion["review_recommended"]),
        "primary_issue": explain["primary_issue"],
        "detected_issues": fusion["detected_issue_types"], "issues": fusion["issues"],
        "statistics": statistics, "dimensions": fusion["dimensions"],
        "signal_agreement": fusion["signal_agreement"], "anomaly": fusion["anomaly"],
        "forensics": explain["forensics"], "narrative": explain["narrative"],
        "thumbnail_path": thumb_path, "heatmap_path": heatmap_path,
        "problem_regions_path": problem_path,
        "model_name": MODEL_NAME, "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION, "pipeline_version": PIPELINE_VERSION,
        "analysis_time_ms": elapsed_ms,
    }
    log_context(logger, 20, "analysis complete", request_id=request_id, id=analysis_id,
                dims=f"{w}x{h}", score=fusion["quality_score"], ms=elapsed_ms,
                model_version=MODEL_VERSION)
    return response, db_record
