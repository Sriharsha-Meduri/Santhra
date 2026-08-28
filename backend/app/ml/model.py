"""Learned models for Santhra.

Two lightweight, CPU-friendly networks:

1. ``SanthraNet`` - a multi-task classifier built on a MobileNetV3-Small
   backbone (ImageNet transfer learning). One shared trunk feeds three heads:

   * quality-class head   (3-way softmax: ACCEPTABLE/DEGRADED/POTENTIALLY_DEFECTIVE)
   * issue head           (7-way multi-label sigmoid - an image can be blurry
                            AND noisy AND dark simultaneously)
   * score head           (scalar 0..100 quality regression)

   MobileNetV3-Small is chosen deliberately: ~2.5M params, fast CPU inference,
   small deployment footprint, and a clean last-conv layer for Grad-CAM.

2. ``ConvAutoencoder`` - a small conv AE trained ONLY on clean images. High
   reconstruction error flags a *potential visual anomaly* (not a confirmed
   defect). This is the "learned normal distribution" signal.
"""
from __future__ import annotations

import torch
import torch.nn as nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

from ..config import ISSUE_TYPES, QUALITY_CLASSES

_TRUNK_IN = 576   # MobileNetV3-Small pooled feature width
_TRUNK_OUT = 1024


class SanthraNet(nn.Module):
    """Multi-task image-quality network (MobileNetV3-Small backbone)."""

    def __init__(
        self,
        n_issues: int = len(ISSUE_TYPES),
        n_classes: int = len(QUALITY_CLASSES),
        pretrained: bool = True,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        backbone = mobilenet_v3_small(weights=weights)
        self.features = backbone.features       # last conv block => Grad-CAM target
        self.avgpool = backbone.avgpool
        self.trunk = nn.Sequential(
            nn.Linear(_TRUNK_IN, _TRUNK_OUT),
            nn.Hardswish(inplace=True),
            nn.Dropout(p=dropout),
        )
        self.head_class = nn.Linear(_TRUNK_OUT, n_classes)
        self.head_issues = nn.Linear(_TRUNK_OUT, n_issues)
        self.head_score = nn.Linear(_TRUNK_OUT, 1)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        feat = self.features(x)
        z = torch.flatten(self.avgpool(feat), 1)
        z = self.trunk(z)
        return {
            "class_logits": self.head_class(z),
            "issue_logits": self.head_issues(z),
            "score": self.head_score(z).squeeze(1),
        }

    @property
    def gradcam_target(self) -> nn.Module:
        """Last convolutional module - the layer Grad-CAM hooks."""
        return self.features[-1]


class ConvAutoencoder(nn.Module):
    """Small convolutional autoencoder for clean-image anomaly detection."""

    def __init__(self, base: int = 32) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, base, 4, 2, 1), nn.BatchNorm2d(base), nn.ReLU(True),      # 128->64
            nn.Conv2d(base, base * 2, 4, 2, 1), nn.BatchNorm2d(base * 2), nn.ReLU(True),  # 64->32
            nn.Conv2d(base * 2, base * 4, 4, 2, 1), nn.BatchNorm2d(base * 4), nn.ReLU(True),  # 32->16
            nn.Conv2d(base * 4, base * 4, 4, 2, 1), nn.BatchNorm2d(base * 4), nn.ReLU(True),  # 16->8
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(base * 4, base * 4, 4, 2, 1), nn.BatchNorm2d(base * 4), nn.ReLU(True),  # 8->16
            nn.ConvTranspose2d(base * 4, base * 2, 4, 2, 1), nn.BatchNorm2d(base * 2), nn.ReLU(True),  # 16->32
            nn.ConvTranspose2d(base * 2, base, 4, 2, 1), nn.BatchNorm2d(base), nn.ReLU(True),          # 32->64
            nn.ConvTranspose2d(base, 3, 4, 2, 1), nn.Sigmoid(),                                        # 64->128
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


def build_classifier(pretrained: bool = True) -> SanthraNet:
    """Instantiate the classifier, gracefully falling back to random init if
    pretrained weights cannot be downloaded (offline environments)."""
    try:
        return SanthraNet(pretrained=pretrained)
    except Exception as exc:  # pragma: no cover - network dependent
        print(f"[model] pretrained weights unavailable ({exc}); using random init")
        return SanthraNet(pretrained=False)
