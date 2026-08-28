"""Deterministic preprocessing shared by training and inference.

Keeping these transforms in one place guarantees that what the model sees at
inference time is identical to training (a common source of silent bugs).
"""
from __future__ import annotations

import numpy as np
import torch

from ..config import (
    ANOMALY_INPUT_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    MODEL_INPUT_SIZE,
)

_MEAN = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
_STD = torch.tensor(IMAGENET_STD).view(3, 1, 1)


def _resize(image_rgb: np.ndarray, size: int) -> np.ndarray:
    import cv2

    return cv2.resize(image_rgb, (size, size), interpolation=cv2.INTER_AREA)


def to_classifier_tensor(image_rgb: np.ndarray) -> torch.Tensor:
    """RGB uint8 (H,W,3) -> normalised CxHxH float tensor for the classifier."""
    resized = _resize(image_rgb, MODEL_INPUT_SIZE).astype(np.float32) / 255.0
    t = torch.from_numpy(resized).permute(2, 0, 1)
    return (t - _MEAN) / _STD


def to_anomaly_tensor(image_rgb: np.ndarray) -> torch.Tensor:
    """RGB uint8 (H,W,3) -> [0,1] CxHxH tensor for the autoencoder."""
    resized = _resize(image_rgb, ANOMALY_INPUT_SIZE).astype(np.float32) / 255.0
    return torch.from_numpy(resized).permute(2, 0, 1)


def anomaly_tensor_to_rgb01(t: torch.Tensor) -> np.ndarray:
    """CxHxW [0,1] tensor -> HxWx3 float image for residual visualisation."""
    return t.detach().cpu().clamp(0, 1).permute(1, 2, 0).numpy()
