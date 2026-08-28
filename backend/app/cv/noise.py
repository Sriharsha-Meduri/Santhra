"""Image-noise features."""
from __future__ import annotations

import cv2
import numpy as np
from skimage.restoration import estimate_sigma

from ..core.logging import get_logger
from .utils import luminance01, normalize_map, safe_float

logger = get_logger("santhra.cv.noise")


def extract(image_rgb: np.ndarray) -> dict[str, float]:
    """Estimate noise using complementary methods.

    * ``noise_sigma`` - skimage wavelet-based sigma estimate (0..255 scale),
      averaged across channels; robust to content.
    * ``hf_residual_std`` - std of (image - median-filtered image); captures
      high-frequency grain.
    * ``local_flat_variance`` - mean variance measured in the *flattest* tiles
      (low-texture regions where noise dominates).
    """
    lum = (luminance01(image_rgb) * 255.0).astype(np.float32)
    med = cv2.medianBlur(lum.astype(np.uint8), 3).astype(np.float32)
    residual = lum - med
    hf_residual_std = safe_float(residual.std())

    try:
        sigma = estimate_sigma(image_rgb, channel_axis=-1, average_sigmas=True)
        noise_sigma = safe_float(sigma)
    except Exception as exc:
        # Fall back to the high-frequency residual (a real measurement on the
        # same 0..255 scale) rather than fabricating a "0 noise" reading.
        logger.warning("estimate_sigma failed (%s); using hf-residual fallback", exc)
        noise_sigma = hf_residual_std

    # local variance in the flattest 20% of tiles
    tile = 16
    h, w = lum.shape
    hh, ww = (h // tile) * tile, (w // tile) * tile
    local_flat_variance = 0.0
    if hh >= tile and ww >= tile:
        tiles = lum[:hh, :ww].reshape(hh // tile, tile, ww // tile, tile)
        var = tiles.var(axis=(1, 3)).reshape(-1)
        k = max(1, int(0.2 * var.size))
        local_flat_variance = safe_float(np.sort(var)[:k].mean())

    return {
        "noise_sigma": noise_sigma,
        "hf_residual_std": hf_residual_std,
        "local_flat_variance": local_flat_variance,
    }


def noise_map(image_rgb: np.ndarray, ksize: int = 9) -> np.ndarray:
    """Local high-frequency energy map (noise localisation), normalised."""
    lum = (luminance01(image_rgb) * 255.0).astype(np.float32)
    med = cv2.medianBlur(lum.astype(np.uint8), 3).astype(np.float32)
    residual = np.abs(lum - med)
    energy = cv2.blur(residual, (ksize, ksize))
    return normalize_map(energy)
