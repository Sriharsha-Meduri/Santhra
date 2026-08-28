"""Santhra API application factory."""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import routes_analysis, routes_health, routes_history
from .config import APP_VERSION, REPO_ROOT, get_settings
from .core.exceptions import SanthraError
from .core.logging import configure_logging, get_logger, log_context

DESCRIPTION = """
**Santhra** - AI-powered image quality & defect intelligence.

A hybrid-intelligence pipeline: a learned multi-task CNN (MobileNetV3-Small) and
a classical CV feature engine are fused into an auditable quality report with
per-issue severity, temperature-calibrated class probabilities, a confidence
level, signal-agreement, Grad-CAM/CV heatmaps, and Quality Forensics. No
external AI services; runs fully locally.
"""

logger = get_logger("santhra.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the DB and models once on startup so /health is accurate."""
    from .db.database import init_db
    from .services.inference_service import get_engine

    init_db()
    engine = get_engine()
    log_context(logger, 20, "startup complete", model_loaded=engine.model_loaded,
                anomaly_loaded=engine.anomaly_loaded, device=engine.device)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Santhra API",
        version=APP_VERSION,
        description=DESCRIPTION,
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = uuid.uuid4().hex[:12]
        request.state.request_id = rid
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        if request.url.path.startswith("/api"):
            log_context(logger, 20, "request", request_id=rid, method=request.method,
                        path=request.url.path, status=response.status_code,
                        ms=round((time.perf_counter() - start) * 1000, 1))
        return response

    @app.exception_handler(SanthraError)
    async def handle_domain_error(request: Request, exc: SanthraError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "detail": exc.message,
                     "request_id": getattr(request.state, "request_id", None)},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", None)
        log_context(logger, 40, "unhandled error", request_id=rid, error=repr(exc))
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error",
                     "detail": "An unexpected error occurred.", "request_id": rid},
        )

    media_dir = REPO_ROOT / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

    app.include_router(routes_health.router)
    app.include_router(routes_analysis.router)
    app.include_router(routes_history.router)

    @app.get("/", tags=["health"])
    def root() -> dict:
        return {"name": "Santhra API", "version": APP_VERSION,
                "docs": "/docs", "health": "/health"}

    return app


app = create_app()
