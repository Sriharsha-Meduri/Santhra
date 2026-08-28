"""Health & readiness endpoints (real checks, no fake values)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import APP_VERSION, MODEL_NAME, MODEL_VERSION
from ..db.database import db_healthy
from ..services.inference_service import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> JSONResponse:
    engine = get_engine()
    db_ok = db_healthy()
    ok = engine.model_loaded and db_ok
    body = {
        "status": "healthy" if ok else "degraded",
        "model_loaded": engine.model_loaded,
        "anomaly_model_loaded": engine.anomaly_loaded,
        "database": "connected" if db_ok else "unavailable",
        "device": engine.device,
        "model": {"name": MODEL_NAME, "version": MODEL_VERSION},
        "version": APP_VERSION,
    }
    # 200 when fully healthy, 503 when degraded so orchestrators/load balancers
    # can key on the status code, not just the body.
    return JSONResponse(status_code=200 if ok else 503, content=body)
