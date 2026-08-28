"""Deterministic, reproducible image-quality degradation library.

Given a clean RGB image and a seeded ``numpy`` Generator, we synthesise a
degraded variant by sampling a *recipe*: pick 0..N degradation groups, and one
degradation within each group (so labels never conflict, e.g. we never apply
both under- and over-exposure). Every applied degradation records the exact
parameters used, which become the ground-truth labels.

Groups map 1:1 to the multi-label issue vocabulary in ``app.config``:

    blur | noise | (under/over)exposure | low_contrast | compression | color_cast

Design choices that matter for the assessment:

* Reproducible: identical (image, seed) -> identical output + labels.
* Honest labels: an issue label is set iff that degradation was actually
  applied; severity is derived from the sampled parameter, not guessed.
* Leakage-safe by construction: this operates on a single source image; the
  train/val/test split is done on *source images* upstream (see build_dataset).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import cv2
import numpy as np

ISSUES = [
    "blur",
    "underexposure",
    "overexposure",
    "noise",
    "low_contrast",
    "compression",
    "color_cast",
]


@dataclass
class Variant:
    image: np.ndarray
    issues: dict[str, int]           # multi-label 0/1 per issue
    severities: dict[str, float]     # 0..1 per applied issue
    quality_class: str               # ACCEPTABLE | DEGRADED | POTENTIALLY_DEFECTIVE
    score: float                     # 0..100 regression target
    params: dict = field(default_factory=dict)

    @property
    def issue_vector(self) -> list[int]:
        return [self.issues[i] for i in ISSUES]


def _lin(v: float, lo: float, hi: float) -> float:
    return float(np.clip((v - lo) / (hi - lo + 1e-9), 0.0, 1.0))


# --------------------------------------------------------------------------- #
# Individual degradations: (image, rng) -> (image, severity, params)
# --------------------------------------------------------------------------- #
def gaussian_blur(img, rng):
    sigma = float(rng.uniform(1.2, 5.5))
    out = cv2.GaussianBlur(img, (0, 0), sigmaX=sigma)
    return out, _lin(sigma, 1.2, 5.5), {"blur_type": "gaussian", "blur_sigma": round(sigma, 3)}


def motion_blur(img, rng):
    length = int(rng.integers(9, 27))
    angle = float(rng.uniform(0, 180))
    k = np.zeros((length, length), np.float32)
    k[length // 2, :] = 1.0
    M = cv2.getRotationMatrix2D((length / 2, length / 2), angle, 1.0)
    k = cv2.warpAffine(k, M, (length, length))
    k /= k.sum() + 1e-9
    out = cv2.filter2D(img, -1, k)
    return out, _lin(length, 9, 27), {"blur_type": "motion", "motion_length": length, "motion_angle": round(angle, 1)}


def gaussian_noise(img, rng):
    std = float(rng.uniform(10, 48))
    noise = rng.normal(0, std, img.shape)
    out = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return out, _lin(std, 10, 48), {"noise_type": "gaussian", "noise_std": round(std, 3)}


def poisson_noise(img, rng):
    peak = float(rng.uniform(12, 90))          # lower peak == more noise
    scaled = img.astype(np.float32) / 255.0 * peak
    noisy = rng.poisson(scaled).astype(np.float32) / peak * 255.0
    out = np.clip(noisy, 0, 255).astype(np.uint8)
    return out, _lin(90 - peak, 0, 78), {"noise_type": "poisson", "poisson_peak": round(peak, 2)}


def underexpose(img, rng):
    factor = float(rng.uniform(0.20, 0.55))
    out = np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)
    return out, _lin(0.55 - factor, 0, 0.35), {"brightness_factor": round(factor, 3)}


def overexpose(img, rng):
    factor = float(rng.uniform(1.7, 3.2))
    out = np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)
    return out, _lin(factor, 1.7, 3.2), {"brightness_factor": round(factor, 3)}


def reduce_contrast(img, rng):
    alpha = float(rng.uniform(0.22, 0.6))
    mean = img.reshape(-1, 3).mean(axis=0)
    out = np.clip(mean + alpha * (img.astype(np.float32) - mean), 0, 255).astype(np.uint8)
    return out, _lin(0.6 - alpha, 0, 0.38), {"contrast_alpha": round(alpha, 3)}


def jpeg_compress(img, rng):
    quality = int(rng.integers(6, 42))
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    ok, enc = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return img, 0.0, {}
    dec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    out = cv2.cvtColor(dec, cv2.COLOR_BGR2RGB)
    return out, _lin(42 - quality, 0, 36), {"jpeg_quality": quality}


def color_distort(img, rng):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.float32)
    if rng.random() < 0.5:                       # desaturate
        s = float(rng.uniform(0.2, 0.55))
        hsv[:, :, 1] *= s
        sev = _lin(0.55 - s, 0, 0.35)
        params = {"color_mode": "desaturate", "saturation_scale": round(s, 3)}
    else:                                         # channel gain cast
        gains = rng.uniform([1.15, 0.8, 0.8], [1.5, 1.0, 1.0])
        rng.shuffle(gains)
        rgb = np.clip(img.astype(np.float32) * gains, 0, 255).astype(np.uint8)
        sev = _lin(float(np.max(gains) - np.min(gains)), 0, 0.7)
        return rgb, sev, {"color_mode": "cast", "channel_gains": [round(float(g), 3) for g in gains]}
    out = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB)
    return out, sev, params


GROUPS: dict[str, list[tuple[str, Callable]]] = {
    "blur": [("blur", gaussian_blur), ("blur", motion_blur)],
    "noise": [("noise", gaussian_noise), ("noise", poisson_noise)],
    "exposure": [("underexposure", underexpose), ("overexposure", overexpose)],
    "low_contrast": [("low_contrast", reduce_contrast)],
    "compression": [("compression", jpeg_compress)],
    "color_cast": [("color_cast", color_distort)],
}


def _quality_class(issues: dict[str, int], severities: dict[str, float]) -> str:
    n = sum(issues.values())
    max_sev = max(severities.values()) if severities else 0.0
    if n == 0:
        return "ACCEPTABLE"
    if n >= 3 or max_sev >= 0.75:
        return "POTENTIALLY_DEFECTIVE"
    return "DEGRADED"


def _score(severities: dict[str, float]) -> float:
    """0..100 quality target: each issue multiplicatively erodes quality."""
    q = 1.0
    for s in severities.values():
        q *= (1.0 - 0.9 * s)
    return round(100.0 * q, 1)


def generate_variant(clean_rgb: np.ndarray, rng: np.random.Generator,
                     clean_prob: float = 0.18, max_ops: int = 3) -> Variant:
    """Sample one degraded (or clean) variant from a clean source image."""
    issues = {i: 0 for i in ISSUES}
    severities: dict[str, float] = {}
    params: dict = {}
    img = clean_rgb.copy()

    if rng.random() >= clean_prob:
        group_names = list(GROUPS.keys())
        k = int(rng.integers(1, max_ops + 1))
        chosen = rng.choice(group_names, size=min(k, len(group_names)), replace=False)
        for gname in chosen:
            options = GROUPS[gname]
            issue, fn = options[int(rng.integers(0, len(options)))]
            img, sev, p = fn(img, rng)
            issues[issue] = 1
            severities[issue] = round(float(sev), 3)
            params.update(p)

    qclass = _quality_class(issues, severities)
    score = _score(severities)
    return Variant(image=img, issues=issues, severities=severities,
                   quality_class=qclass, score=score, params=params)
