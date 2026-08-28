"""Contrast / dynamic-range features."""
from __future__ import annotations

import numpy as np

from .utils import luminance01, safe_float


def extract(image_rgb: np.ndarray) -> dict[str, float]:
    """Compute contrast descriptors.

    * ``rms_contrast`` - standard deviation of luminance (global RMS contrast).
    * ``percentile_spread`` - robust p5..p95 luminance spread.
    * ``dynamic_range`` - p1..p99 range (tone coverage).
    * ``local_contrast`` - mean of local std over 16x16 tiles.
    """
    lum = luminance01(image_rgb)
    flat = lum.reshape(-1)

    p1, p5, p95, p99 = np.percentile(flat, [1, 5, 95, 99])

    # local contrast on non-overlapping tiles
    h, w = lum.shape
    tile = 16
    hh, ww = (h // tile) * tile, (w // tile) * tile
    local = 0.0
    if hh >= tile and ww >= tile:
        tiles = lum[:hh, :ww].reshape(hh // tile, tile, ww // tile, tile)
        local = float(tiles.std(axis=(1, 3)).mean())

    return {
        "rms_contrast": safe_float(flat.std()),
        "percentile_spread": safe_float(p95 - p5),
        "dynamic_range": safe_float(p99 - p1),
        "local_contrast": safe_float(local),
    }
