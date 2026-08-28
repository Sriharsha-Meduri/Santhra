"""JPEG / block-compression artifact features."""
from __future__ import annotations

import numpy as np

from .utils import luminance01, safe_float

BLOCK = 8


def extract(image_rgb: np.ndarray) -> dict[str, float]:
    """Estimate blocking artifacts using an 8x8 boundary-discontinuity metric.

    JPEG compresses in 8x8 blocks, so heavy compression creates step
    discontinuities aligned to that grid. We compare the mean absolute
    difference *across* block boundaries with the mean *inside* blocks.

    * ``blockiness`` - boundary/interior ratio (≈1 clean, >1.1 blocky).
    * ``block_boundary_energy`` - raw boundary discontinuity strength.
    """
    lum = luminance01(image_rgb) * 255.0
    h, w = lum.shape

    dh = np.abs(np.diff(lum, axis=1))  # horizontal neighbour diffs
    dv = np.abs(np.diff(lum, axis=0))  # vertical neighbour diffs

    def _ratio(diff: np.ndarray, axis_len: int, axis: int) -> tuple[float, float]:
        idx = np.arange(diff.shape[axis])
        boundary = (idx % BLOCK) == (BLOCK - 1)
        if boundary.sum() == 0 or (~boundary).sum() == 0:
            return 0.0, 0.0
        if axis == 1:
            b = diff[:, boundary].mean()
            i = diff[:, ~boundary].mean()
        else:
            b = diff[boundary, :].mean()
            i = diff[~boundary, :].mean()
        return float(b), float(i)

    bh, ih = _ratio(dh, w, axis=1)
    bv, iv = _ratio(dv, h, axis=0)

    boundary_energy = (bh + bv) / 2.0
    interior_energy = (ih + iv) / 2.0
    blockiness = safe_float(boundary_energy / (interior_energy + 1e-6))

    return {
        "blockiness": blockiness,
        "block_boundary_energy": safe_float(boundary_energy),
    }
