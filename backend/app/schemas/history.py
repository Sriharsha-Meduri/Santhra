"""Pydantic models for history listing and detail."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class HistoryItem(BaseModel):
    id: str
    created_at: str
    filename: str
    quality_score: int
    quality_label: str
    quality_class: str
    overall_confidence: str
    review_recommended: bool
    primary_issue: str | None
    thumbnail_url: str | None


class HistoryList(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


class AnalysisDetail(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: str
    created_at: str
    filename: str
    format: str
    image: dict[str, Any]
    quality_score: int
    quality_label: str
    quality_class: str
    overall_confidence: str
    review_recommended: bool
    primary_issue: str | None
    detected_issues: list[str]
    issues: list[dict[str, Any]]
    statistics: dict[str, Any]
    dimensions: dict[str, Any]
    signal_agreement: dict[str, Any]
    anomaly: dict[str, Any]
    forensics: list[dict[str, Any]]
    narrative: str
    thumbnail_url: str | None
    heatmap_url: str | None
    problem_regions_url: str | None
    model_info: dict[str, Any]
    analysis_time_ms: float
