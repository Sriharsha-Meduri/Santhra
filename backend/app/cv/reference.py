"""Reference ranges that turn raw CV measurements into interpretable [0,1]
severities and 0-100 quality dimensions.

These thresholds are the *measured-signal* opinion of the classical CV engine.
They are intentionally centralised (no magic numbers scattered in the fusion
code) and were chosen to bracket the synthetic degradation ranges used in
training (see ml/datasets/degradations.py) - documented in docs/architecture.md.
The learned model provides the complementary opinion; the fusion layer combines
the two.
"""
from __future__ import annotations

import math


def _ramp(x: float, lo: float, hi: float) -> float:
    """0 at ``lo``, 1 at ``hi`` (monotone increasing severity)."""
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def cv_issue_severities(f: dict) -> dict[str, float]:
    """Per-issue severity in [0,1] derived purely from CV measurements."""
    lapvar = max(f["sharpness"]["laplacian_variance"], 1e-3)
    # blur: sharp images have high log-Laplacian variance
    blur = 1.0 - _ramp(math.log10(lapvar), math.log10(8.0), math.log10(250.0))

    mean_lum = f["exposure"]["mean_luminance"]
    under = max(_ramp(0.32 - mean_lum, 0.0, 0.14),
                _ramp(f["exposure"]["dark_fraction"], 0.45, 0.85))
    over = max(_ramp(mean_lum - 0.62, 0.0, 0.14),
               _ramp(f["exposure"]["high_clip_fraction"], 0.03, 0.20))

    noise = max(_ramp(f["noise"]["noise_sigma"], 3.0, 14.0),
                _ramp(f["noise"]["hf_residual_std"], 3.5, 12.0))

    low_contrast = max(_ramp(0.40 - f["contrast"]["percentile_spread"], 0.0, 0.24),
                       _ramp(0.16 - f["contrast"]["rms_contrast"], 0.0, 0.10))

    compression = _ramp(f["compression"]["blockiness"], 1.06, 1.30)

    color = max(_ramp(f["color"]["color_cast"], 0.09, 0.28),
                _ramp(0.30 - f["color"]["saturation_mean"], 0.0, 0.22))

    return {
        "blur": round(blur, 4),
        "underexposure": round(under, 4),
        "overexposure": round(over, 4),
        "noise": round(noise, 4),
        "low_contrast": round(low_contrast, 4),
        "compression": round(compression, 4),
        "color_cast": round(color, 4),
    }


def dimension_scores(f: dict) -> dict[str, float]:
    """0-100 per-dimension quality (higher == better) for the radar chart."""
    sev = cv_issue_severities(f)
    integrity = 1.0
    if f["integrity"]["entropy"] < 3.0 or f["integrity"]["uniformity"] > 0.6:
        integrity = 0.3
    dims = {
        "sharpness": 1.0 - sev["blur"],
        "exposure": 1.0 - max(sev["underexposure"], sev["overexposure"]),
        "noise": 1.0 - sev["noise"],
        "contrast": 1.0 - sev["low_contrast"],
        "color": 1.0 - sev["color_cast"],
        "integrity": integrity,
    }
    return {k: round(100.0 * v, 1) for k, v in dims.items()}
