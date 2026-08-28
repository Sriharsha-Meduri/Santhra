"""Shared helpers for the classical-CV feature engine.

All feature functions in this package agree on one convention:

* input images are RGB ``uint8`` NumPy arrays of shape ``(H, W, 3)``
* luminance is BT.601 on the ``[0, 1]`` range
"""
from __future__ import annotations

import cv2
import numpy as np

from ..config import CV_MAX_SIDE

# BT.601 luma coefficients
_LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def ensure_rgb_uint8(image: np.ndarray) -> np.ndarray:
    """Coerce arbitrary decoded image arrays into RGB uint8 (H, W, 3)."""
    arr = np.asarray(image)
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
    elif arr.ndim == 3 and arr.shape[2] == 4:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
    elif arr.ndim == 3 and arr.shape[2] == 1:
        arr = cv2.cvtColor(arr[:, :, 0], cv2.COLOR_GRAY2RGB)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"Cannot coerce array of shape {arr.shape} to RGB")
    return np.ascontiguousarray(arr)


def luminance01(image_rgb: np.ndarray) -> np.ndarray:
    """Return BT.601 luminance in ``[0, 1]`` as float32."""
    rgb = image_rgb.astype(np.float32) / 255.0
    return rgb @ _LUMA


def resize_max_side(image_rgb: np.ndarray, max_side: int = CV_MAX_SIDE) -> np.ndarray:
    """Downscale so the longest side <= ``max_side`` (keeps CV metrics fast)."""
    h, w = image_rgb.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return image_rgb
    scale = max_side / float(longest)
    new_size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    return cv2.resize(image_rgb, new_size, interpolation=cv2.INTER_AREA)


def normalize_map(m: np.ndarray, percentile: float = 99.0) -> np.ndarray:
    """Robustly normalise a heatmap to ``[0, 1]`` (percentile clip)."""
    m = m.astype(np.float32)
    lo = float(np.min(m))
    hi = float(np.percentile(m, percentile))
    if hi - lo < 1e-8:
        return np.zeros_like(m)
    return np.clip((m - lo) / (hi - lo), 0.0, 1.0)


def safe_float(x: float, default: float = 0.0) -> float:
    """Return a JSON-safe finite float."""
    xf = float(x)
    if not np.isfinite(xf):
        return default
    return xf
