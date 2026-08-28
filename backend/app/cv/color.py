"""Colour / saturation / colour-cast features."""
from __future__ import annotations

import cv2
import numpy as np

from .utils import safe_float


def extract(image_rgb: np.ndarray) -> dict[str, float]:
    """Compute colour descriptors.

    * ``saturation_mean`` / ``saturation_std`` - HSV saturation on ``[0, 1]``.
    * ``channel_imbalance`` - max-min of per-channel means (0..1); large values
      hint at a colour cast or a near-monochrome image.
    * ``color_cast`` - distance of the mean LAB (a, b) chroma from neutral
      grey; a strong global tint (e.g. blue/orange cast) raises this.
    """
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.0

    rgb = image_rgb.astype(np.float32) / 255.0
    means = rgb.reshape(-1, 3).mean(axis=0)
    channel_imbalance = safe_float(means.max() - means.min())

    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    # OpenCV LAB: a,b in [0,255] centred at 128 == neutral
    a_dev = lab[:, :, 1].mean() - 128.0
    b_dev = lab[:, :, 2].mean() - 128.0
    color_cast = safe_float(np.sqrt(a_dev**2 + b_dev**2) / 128.0)

    return {
        "saturation_mean": safe_float(sat.mean()),
        "saturation_std": safe_float(sat.std()),
        "channel_imbalance": channel_imbalance,
        "color_cast": color_cast,
    }
