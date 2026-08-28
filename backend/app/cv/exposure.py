"""Exposure / brightness-clipping features."""
from __future__ import annotations

import numpy as np

from .utils import luminance01, safe_float

DARK_THRESHOLD = 0.20
BRIGHT_THRESHOLD = 0.80
LOW_CLIP = 0.02
HIGH_CLIP = 0.98


def extract(image_rgb: np.ndarray) -> dict[str, float]:
    """Compute exposure descriptors on ``[0, 1]`` luminance.

    * ``mean_luminance`` / ``median_luminance`` - overall brightness.
    * ``dark_fraction`` / ``bright_fraction`` - share of very dark / bright px.
    * ``low_clip_fraction`` / ``high_clip_fraction`` - shadow / highlight
      clipping (lost detail at the extremes).
    * ``luminance_entropy`` - histogram entropy (spread of tones).
    """
    lum = luminance01(image_rgb)
    flat = lum.reshape(-1)

    hist, _ = np.histogram(flat, bins=256, range=(0.0, 1.0), density=True)
    p = hist / (hist.sum() + 1e-12)
    entropy = safe_float(-(p[p > 0] * np.log2(p[p > 0])).sum())

    return {
        "mean_luminance": safe_float(flat.mean()),
        "median_luminance": safe_float(np.median(flat)),
        "dark_fraction": safe_float((flat < DARK_THRESHOLD).mean()),
        "bright_fraction": safe_float((flat > BRIGHT_THRESHOLD).mean()),
        "low_clip_fraction": safe_float((flat < LOW_CLIP).mean()),
        "high_clip_fraction": safe_float((flat > HIGH_CLIP).mean()),
        "luminance_entropy": entropy,
    }


def clipping_map(image_rgb: np.ndarray) -> np.ndarray:
    """Binary-ish map of clipped shadow/highlight pixels (problem regions)."""
    lum = luminance01(image_rgb)
    m = ((lum < LOW_CLIP) | (lum > HIGH_CLIP)).astype(np.float32)
    return m
