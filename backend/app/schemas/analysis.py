"""Pydantic response models for analysis (drives Swagger docs)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ImageInfo(BaseModel):
    width: int
    height: int
    channels: int
    megapixels: float
    aspect_ratio: float
    file_size_kb: float


class IssueOut(BaseModel):
    type: str
    detected: bool
    severity: str
    severity_value: float
    confidence: float
    ml_probability: float
    cv_severity: float
    agreement: float
    evidence: dict[str, float]


class ExplainabilityOut(BaseModel):
    primary_issue: str | None
    heatmap: str | None
    heatmap_method: str
    problem_regions: str | None
    problem_method: str
    forensics: list[dict[str, Any]]
    evidence_cards: list[dict[str, Any]]
    narrative: str


class ModelInfoOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str
    model_version: str
    feature_version: str
    pipeline_version: str
    app_version: str
    model_score: float
    cv_score: float
    device: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: str
    created_at: str
    filename: str
    format: str
    image: ImageInfo
    quality_score: int
    quality_label: str
    quality_class: str
    class_probabilities: dict[str, float]
    overall_confidence: str
    overall_confidence_value: float
    review_recommended: bool
    review_reasons: list[str]
    issues: list[IssueOut]
    detected_issue_types: list[str]
    dimensions: dict[str, float]
    statistics: dict[str, Any]
    signal_agreement: dict[str, Any]
    anomaly: dict[str, Any]
    integrity: dict[str, Any]
    explainability: ExplainabilityOut
    model_info: ModelInfoOut
    analysis_time_ms: float


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str | None = None
