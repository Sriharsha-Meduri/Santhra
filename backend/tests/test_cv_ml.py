"""Unit tests for the CV feature engine and the ML inference layer."""
from __future__ import annotations

import cv2
import numpy as np

from app.cv import exposure, noise, sharpness
from app.ml.model import SanthraNet
from app.ml.preprocessing import to_classifier_tensor
from app.services.feature_service import extract_features
from app.services.inference_service import get_engine


def _img(seed=0):
    rng = np.random.default_rng(seed)
    return (rng.random((200, 260, 3)) * 150 + 50).astype(np.uint8)


def test_sharpness_discriminates_blur():
    img = _img()
    sharp = sharpness.extract(img)["laplacian_variance"]
    blur = sharpness.extract(cv2.GaussianBlur(img, (0, 0), 5))["laplacian_variance"]
    assert sharp > blur * 3


def test_exposure_detects_dark():
    img = _img()
    dark = (img * 0.25).astype(np.uint8)
    assert exposure.extract(dark)["mean_luminance"] < exposure.extract(img)["mean_luminance"]
    assert exposure.extract(dark)["dark_fraction"] > 0.3


def test_noise_estimation_discriminates():
    # Guards the estimate_sigma path (needs PyWavelets): a noisy image must
    # report a higher noise_sigma than a smooth one, and it must be non-zero.
    smooth = cv2.GaussianBlur(_img(3), (0, 0), 3)
    noisy = np.clip(smooth + np.random.default_rng(1).normal(0, 30, smooth.shape),
                    0, 255).astype(np.uint8)
    n_smooth = noise.extract(smooth)["noise_sigma"]
    n_noisy = noise.extract(noisy)["noise_sigma"]
    assert n_noisy > 0.0
    assert n_noisy > n_smooth


def test_feature_service_structure_and_bounds():
    out = extract_features(_img(), file_size_bytes=40000)
    assert set(out["features"]) == {"sharpness", "exposure", "contrast", "noise",
                                    "compression", "color", "integrity"}
    for v in out["dimensions"].values():
        assert 0.0 <= v <= 100.0
    for v in out["cv_issue_severities"].values():
        assert 0.0 <= v <= 1.0


def test_preprocessing_shape():
    t = to_classifier_tensor(_img())
    assert tuple(t.shape) == (3, 224, 224)


def test_model_forward_shapes():
    import torch

    m = SanthraNet(pretrained=False).eval()
    with torch.no_grad():
        out = m(torch.zeros(2, 3, 224, 224))
    assert out["class_logits"].shape == (2, 3)
    assert out["issue_logits"].shape == (2, 7)
    assert out["score"].shape == (2,)


def test_inference_bounds_and_determinism():
    engine = get_engine()
    img = _img(2)
    a = engine.predict(img)
    b = engine.predict(img)
    assert 0 <= a["model_score"] <= 100
    for p in a["issue_probs"].values():
        assert 0.0 <= p <= 1.0
    assert abs(sum(a["class_probs"].values()) - 1.0) < 1e-4
    assert a["model_score"] == b["model_score"]          # deterministic


def test_fusion_is_hybrid_not_cnn_only():
    """The measured CV signal must actually change the decision, and a strong
    ML-vs-CV disagreement must be represented (not averaged away). This is what
    makes the 'hybrid' and 'signal agreement' claims computationally real."""
    from app.config import ISSUE_TYPES, STRONG_DISAGREE
    from app.services.fusion_service import fuse

    feats = {
        "sharpness": {"laplacian_variance": 0.0, "edge_density": 0.0},
        "exposure": {"mean_luminance": 0.5, "dark_fraction": 0.0, "high_clip_fraction": 0.0},
        "noise": {"noise_sigma": 0.0, "hf_residual_std": 0.0},
        "contrast": {"percentile_spread": 0.0, "rms_contrast": 0.0},
        "compression": {"blockiness": 1.0},
        "color": {"color_cast": 0.0, "saturation_mean": 0.3},
        "integrity": {"entropy": 7.5, "uniformity": 0.1, "constant_row_fraction": 0.0},
    }
    dims = {d: 50 for d in ("sharpness", "exposure", "noise", "contrast", "color", "integrity")}
    ml = {
        "issue_probs": {**{i: 0.02 for i in ISSUE_TYPES}, "blur": 0.10},  # model: NOT blurry
        "class_probs": {"ACCEPTABLE": 0.8, "DEGRADED": 0.15, "POTENTIALLY_DEFECTIVE": 0.05},
        "quality_class": "ACCEPTABLE",
        "model_score": 90.0,
    }
    anomaly = {"anomaly_score": 0.0, "z_score": 0.0, "recon_error": 0.0}

    cv_hi = {"features": feats, "dimensions": dims,
             "cv_issue_severities": {**{i: 0.0 for i in ISSUE_TYPES}, "blur": 0.9}}  # CV: very blurry
    cv_lo = {"features": feats, "dimensions": dims,
             "cv_issue_severities": {i: 0.0 for i in ISSUE_TYPES}}                   # CV: silent

    hi = fuse(ml, cv_hi, anomaly)
    lo = fuse(ml, cv_lo, anomaly)
    blur_hi = next(i for i in hi["issues"] if i["type"] == "blur")

    # (1) CV flips the outcome -> genuine fusion, the score is not just the CNN
    assert blur_hi["detected"] is True
    assert next(i for i in lo["issues"] if i["type"] == "blur")["detected"] is False
    # (2) signal-agreement is meaningful: a real disagreement reads as low
    assert blur_hi["agreement"] < STRONG_DISAGREE
    # (3) the disagreement drives review-recommended, with a stated reason
    assert hi["review_recommended"] is True
    assert any("blur" in r.lower() for r in hi["review_reasons"])
    # (4) the measured half genuinely moves the fused 0-100 score
    assert hi["quality_score"] < lo["quality_score"]
