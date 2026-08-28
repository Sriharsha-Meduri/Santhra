"""Central configuration, versioning, and label definitions for Santhra.

Everything version-related and every shared label list lives here so that the
backend, the training pipeline, and the documentation cannot drift apart.
Runtime settings are read from environment variables with sensible local
defaults (see ``.env.example``).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
# backend/app/config.py -> parents[2] == repository root
REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DIR = REPO_ROOT / "ml" / "checkpoints"

# --------------------------------------------------------------------------- #
# Versioning  (recorded on every analysis; surfaced via /model/info)
# --------------------------------------------------------------------------- #
MODEL_NAME = "santhra-mtl-mobilenetv3s"
MODEL_VERSION = "1.0.0"
FEATURE_VERSION = "1.0.0"          # bump when CV feature definitions change
PIPELINE_VERSION = "1.0.0"         # bump when fusion logic changes
APP_VERSION = "1.0.0"

# --------------------------------------------------------------------------- #
# Labels  (single source of truth, shared with the training pipeline)
# --------------------------------------------------------------------------- #
# Multi-label issue heads.  An image can exhibit several simultaneously, so
# these are trained with BCEWithLogitsLoss (NOT mutually exclusive).
ISSUE_TYPES: list[str] = [
    "blur",
    "underexposure",
    "overexposure",
    "noise",
    "low_contrast",
    "compression",
    "color_cast",
]

# Mutually-exclusive overall quality class (CrossEntropy head).
QUALITY_CLASSES: list[str] = ["ACCEPTABLE", "DEGRADED", "POTENTIALLY_DEFECTIVE"]

SEVERITY_LEVELS: list[str] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CONFIDENCE_LEVELS: list[str] = ["LOW", "MEDIUM", "HIGH"]

# Human-readable score bands (documented methodology, see fusion_service).
SCORE_BANDS = [
    (90, 100, "EXCELLENT"),
    (75, 89, "ACCEPTABLE"),
    (50, 74, "DEGRADED"),
    (0, 49, "POTENTIALLY_DEFECTIVE"),
]

# --------------------------------------------------------------------------- #
# Fusion / decision constants  (single source of truth for the decision layer)
#
# These are DOMAIN HEURISTICS chosen by hand, not values learned from data. They
# are gathered here (rather than scattered in branches) so the whole decision
# policy is auditable in one place. Provenance and rationale for each is
# documented in docs/constants.md. The only learned parameters in the system are
# the network weights and the temperature-scaling values in calibration.json.
# --------------------------------------------------------------------------- #
# Per-issue detection: fused strength = ML_WEIGHT*p_model + CV_WEIGHT*cv_severity
ISSUE_ML_WEIGHT = 0.55        # learned model slightly favoured for detection
ISSUE_CV_WEIGHT = 0.45
DETECT_THRESHOLD = 0.45       # fused strength at/above which an issue is reported

# Overall 0-100 quality score = mean of the learned and measured half-scores.
SCORE_ML_WEIGHT = 0.5
SCORE_CV_WEIGHT = 0.5
CV_SCORE_SEVERITY_WEIGHT = 0.9   # cv_score = 100*prod(1 - w*severity) per issue

# Per-issue severity buckets, applied to the fused strength [0,1].
FUSED_SEVERITY_BANDS = [(0.88, "CRITICAL"), (0.74, "HIGH"), (0.60, "MEDIUM"), (0.0, "LOW")]

# Signal agreement / review.
AGREEMENT_HIGH = 0.72         # 1-|p_model-cv| at/above this -> signals agree
STRONG_DISAGREE = 0.45        # per-issue agreement below this -> flag for review

# Overall confidence = weighted blend, then bucketed.
ISSUE_CONF_AGREEMENT_WEIGHT = 0.5   # per-issue confidence = agree + strength
ISSUE_CONF_STRENGTH_WEIGHT = 0.5
CONF_AGREEMENT_WEIGHT = 0.5         # overall confidence blend
CONF_MARGIN_WEIGHT = 0.3
CONF_ANOMALY_WEIGHT = 0.2
CONF_HIGH = 0.66              # confidence value at/above -> HIGH, else MEDIUM/LOW
CONF_MEDIUM = 0.45

# Anomaly (autoencoder) score shaping and detection cutoff.
ANOMALY_SIGMOID_CENTER = 2.0  # z-score mapped to 0.5 (score = sigmoid(z - c))
ANOMALY_DETECT = 0.60         # anomaly-score cutoff (~2.4 sigma recon error)

# --------------------------------------------------------------------------- #
# Image / model geometry
# --------------------------------------------------------------------------- #
MODEL_INPUT_SIZE = 224                       # MobileNetV3 native input
ANOMALY_INPUT_SIZE = 128                      # conv-autoencoder input
CV_MAX_SIDE = 1024                            # cap for classical-CV speed
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

SUPPORTED_FORMATS = {"jpeg", "jpg", "png", "bmp", "webp", "tiff"}
SUPPORTED_MIME = {
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
    "image/tiff",
}


@dataclass(frozen=True)
class Settings:
    """Runtime settings, overridable via environment variables."""

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite:///{(REPO_ROOT / 'santhra.db').as_posix()}"
        )
    )
    model_path: str = field(
        default_factory=lambda: os.getenv(
            "MODEL_PATH", str(CHECKPOINT_DIR / "model.pt")
        )
    )
    anomaly_model_path: str = field(
        default_factory=lambda: os.getenv(
            "ANOMALY_MODEL_PATH", str(CHECKPOINT_DIR / "anomaly.pt")
        )
    )
    calibration_path: str = field(
        default_factory=lambda: os.getenv(
            "CALIBRATION_PATH", str(CHECKPOINT_DIR / "calibration.json")
        )
    )
    max_upload_size_mb: int = field(
        default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://localhost:3000,http://localhost:4173",
            ).split(",")
            if o.strip()
        )
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    device: str = field(default_factory=lambda: os.getenv("SANTHRA_DEVICE", "auto"))
    backend_port: int = field(
        default_factory=lambda: int(os.getenv("BACKEND_PORT", "8000"))
    )
    env: str = field(default_factory=lambda: os.getenv("SANTHRA_ENV", "development"))

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_device(preference: str | None = None) -> str:
    """Return 'cuda' if available and not disabled, else 'cpu'."""
    import torch

    pref = (preference or get_settings().device or "auto").lower()
    if pref == "cpu":
        return "cpu"
    if pref == "cuda":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"
