"""Image integrity / corruption / severe-degradation signals."""
from __future__ import annotations

import numpy as np

from .utils import luminance01, safe_float


def extract(image_rgb: np.ndarray, file_size_bytes: int | None = None) -> dict[str, float]:
    """Compute integrity descriptors.

    * ``entropy`` - luminance histogram entropy (bits). Extremely low entropy
      means a near-constant / broken image.
    * ``uniformity`` - fraction of pixels sharing the single most common tone.
    * ``constant_row_fraction`` - share of image rows that are perfectly
      constant (a hallmark of truncated / corrupted decodes).
    * ``bytes_per_pixel`` - file bytes / pixel (useful sanity/compression cue).
    """
    lum = luminance01(image_rgb)
    q = np.clip((lum * 255).astype(np.int32), 0, 255)
    counts = np.bincount(q.reshape(-1), minlength=256).astype(np.float64)
    total = counts.sum()
    p = counts / (total + 1e-12)
    entropy = safe_float(-(p[p > 0] * np.log2(p[p > 0])).sum())
    uniformity = safe_float(counts.max() / (total + 1e-12))

    row_const = np.all(q == q[:, :1], axis=1)
    constant_row_fraction = safe_float(row_const.mean())

    h, w = lum.shape[:2]
    bytes_per_pixel = (
        safe_float(file_size_bytes / (h * w)) if file_size_bytes else 0.0
    )

    return {
        "entropy": entropy,
        "uniformity": uniformity,
        "constant_row_fraction": constant_row_fraction,
        "bytes_per_pixel": bytes_per_pixel,
    }


def is_severely_degraded(integrity: dict[str, float]) -> bool:
    """Heuristic gate for obviously broken images."""
    return (
        integrity.get("entropy", 8.0) < 1.5
        or integrity.get("uniformity", 0.0) > 0.9
        or integrity.get("constant_row_fraction", 0.0) > 0.5
    )
