"""Helpers for anomaly localisation from the convolutional autoencoder.

The autoencoder itself (the *learned* component) lives in ``app.ml.model``.
This module only turns a reconstruction into an interpretable residual map and
scalar, so the classical-CV package stays free of torch dependencies.
"""
from __future__ import annotations

import cv2
import numpy as np

from .utils import normalize_map, safe_float


def reconstruction_residual(original01: np.ndarray, recon01: np.ndarray) -> np.ndarray:
    """Per-pixel L2 residual between an image and its AE reconstruction.

    Both inputs are float ``[0, 1]`` RGB of identical shape. Returns a single
    channel residual map (H, W), blurred slightly for stability.
    """
    diff = (original01.astype(np.float32) - recon01.astype(np.float32)) ** 2
    residual = diff.mean(axis=2)
    residual = cv2.GaussianBlur(residual, (0, 0), sigmaX=1.5)
    return residual


def summarize(residual: np.ndarray) -> dict[str, float]:
    """Scalar anomaly descriptors from a residual map."""
    flat = residual.reshape(-1)
    return {
        "anomaly_mean": safe_float(flat.mean()),
        "anomaly_p99": safe_float(np.percentile(flat, 99)),
        "anomaly_max": safe_float(flat.max()),
    }


def anomaly_map(residual: np.ndarray) -> np.ndarray:
    """Normalised anomaly heatmap in ``[0, 1]`` for the UI overlay."""
    return normalize_map(residual)
