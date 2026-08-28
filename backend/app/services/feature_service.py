"""Aggregates the classical-CV feature engine into one structured result."""
from __future__ import annotations

import numpy as np

from ..config import FEATURE_VERSION
from ..cv import (color, compression, contrast, corruption, exposure, noise,
                  sharpness)
from ..cv.reference import cv_issue_severities, dimension_scores
from ..cv.utils import resize_max_side


def extract_features(image_rgb: np.ndarray, file_size_bytes: int | None = None) -> dict:
    """Run every CV extractor on a (resized) copy and return grouped features."""
    img = resize_max_side(image_rgb)
    features = {
        "sharpness": sharpness.extract(img),
        "exposure": exposure.extract(img),
        "contrast": contrast.extract(img),
        "noise": noise.extract(img),
        "compression": compression.extract(img),
        "color": color.extract(img),
        "integrity": corruption.extract(img, file_size_bytes),
    }
    return {
        "feature_version": FEATURE_VERSION,
        "features": features,
        "cv_issue_severities": cv_issue_severities(features),
        "dimensions": dimension_scores(features),
    }


def build_statistics(image_rgb: np.ndarray, features: dict,
                     file_size_bytes: int | None) -> dict:
    """User-facing image statistics for the results panel."""
    h, w = image_rgb.shape[:2]
    f = features["features"]
    return {
        "width": w,
        "height": h,
        "aspect_ratio": round(w / h, 3) if h else 0.0,
        "channels": int(image_rgb.shape[2]) if image_rgb.ndim == 3 else 1,
        "megapixels": round(w * h / 1e6, 3),
        "file_size_kb": round(file_size_bytes / 1024, 1) if file_size_bytes else None,
        "brightness": round(f["exposure"]["mean_luminance"], 4),
        "contrast": round(f["contrast"]["rms_contrast"], 4),
        "sharpness_laplacian": round(f["sharpness"]["laplacian_variance"], 2),
        "edge_density": round(f["sharpness"]["edge_density"], 4),
        "noise_sigma": round(f["noise"]["noise_sigma"], 3),
        "saturation": round(f["color"]["saturation_mean"], 4),
        "highlight_clipping_pct": round(f["exposure"]["high_clip_fraction"] * 100, 2),
        "shadow_clipping_pct": round(f["exposure"]["low_clip_fraction"] * 100, 2),
        "blockiness": round(f["compression"]["blockiness"], 3),
        "entropy": round(f["integrity"]["entropy"], 3),
    }
