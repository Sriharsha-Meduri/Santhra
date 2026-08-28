"""Persistence model. Large binaries (images/heatmaps) are stored on disk under
``media/<id>/`` and referenced by relative path - never inlined into the DB."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    filename: Mapped[str] = mapped_column(String(160))
    image_hash: Mapped[str] = mapped_column(String(64), index=True)
    format: Mapped[str] = mapped_column(String(16))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    channels: Mapped[int] = mapped_column(Integer)
    file_size_bytes: Mapped[int] = mapped_column(Integer)

    quality_score: Mapped[int] = mapped_column(Integer, index=True)
    quality_label: Mapped[str] = mapped_column(String(32), index=True)
    quality_class: Mapped[str] = mapped_column(String(32))
    overall_confidence: Mapped[str] = mapped_column(String(16))
    review_recommended: Mapped[bool] = mapped_column(Integer, default=0)
    primary_issue: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # structured payloads (JSON -> TEXT on sqlite)
    detected_issues: Mapped[list] = mapped_column(JSON, default=list)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    statistics: Mapped[dict] = mapped_column(JSON, default=dict)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    signal_agreement: Mapped[dict] = mapped_column(JSON, default=dict)
    anomaly: Mapped[dict] = mapped_column(JSON, default=dict)
    forensics: Mapped[list] = mapped_column(JSON, default=list)
    narrative: Mapped[str] = mapped_column(Text, default="")

    # media (on-disk relative paths)
    thumbnail_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    heatmap_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    problem_regions_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # versioning
    model_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(16))
    feature_version: Mapped[str] = mapped_column(String(16))
    pipeline_version: Mapped[str] = mapped_column(String(16))
    analysis_time_ms: Mapped[float] = mapped_column(Float)
