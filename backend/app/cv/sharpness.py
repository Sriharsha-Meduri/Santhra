"""Sharpness / blur features (interpretable, measured signals)."""
from __future__ import annotations

import cv2
import numpy as np

from .utils import luminance01, normalize_map, safe_float


def extract(image_rgb: np.ndarray) -> dict[str, float]:
    """Compute sharpness descriptors.

    * ``laplacian_variance`` - variance of the Laplacian; the canonical
      focus/blur measure. Low values indicate blur.
    * ``tenengrad`` - mean squared Sobel gradient magnitude (focus measure).
    * ``gradient_mean`` / ``gradient_std`` - edge-strength statistics.
    * ``edge_density`` - fraction of Canny edge pixels.
    """
    lum = (luminance01(image_rgb) * 255.0).astype(np.float32)

    lap = cv2.Laplacian(lum, cv2.CV_32F, ksize=3)
    laplacian_variance = safe_float(lap.var())

    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = cv2.magnitude(gx, gy)
    tenengrad = safe_float(np.mean(grad_mag**2))
    gradient_mean = safe_float(grad_mag.mean())
    gradient_std = safe_float(grad_mag.std())

    edges = cv2.Canny(lum.astype(np.uint8), 100, 200)
    edge_density = safe_float((edges > 0).mean())

    return {
        "laplacian_variance": laplacian_variance,
        "tenengrad": tenengrad,
        "gradient_mean": gradient_mean,
        "gradient_std": gradient_std,
        "edge_density": edge_density,
    }


def local_sharpness_map(image_rgb: np.ndarray, ksize: int = 15) -> np.ndarray:
    """Per-pixel local sharpness (local Laplacian energy), normalised to [0,1].

    Used for blur localisation: *dark* regions (low sharpness) are the blurry
    ones, so the returned "problem map" is the inverse.
    """
    lum = (luminance01(image_rgb) * 255.0).astype(np.float32)
    lap = cv2.Laplacian(lum, cv2.CV_32F, ksize=3)
    energy = cv2.blur(lap**2, (ksize, ksize))
    sharp = normalize_map(energy)
    # problem map: weakest sharpness == strongest blur evidence
    return np.clip(1.0 - sharp, 0.0, 1.0)
