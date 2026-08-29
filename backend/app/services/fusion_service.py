"""Transparent fusion / decision layer.

Combines two INDEPENDENT opinions per issue:
    * ML  - the learned model's calibrated probability
    * CV  - the classical measurement's severity
into a fused decision, and derives the overall quality score, a confidence
level (from the calibrated class probabilities plus signal agreement),
signal-agreement, and the "review recommended" state.

Every decision constant is defined in config.py (no magic numbers hidden in
branches) and every output records *both* raw signals so the decision is fully
auditable. Provenance for each constant is in docs/constants.md.
"""
from __future__ import annotations

from ..config import (AGREEMENT_HIGH, ANOMALY_DETECT, CONF_AGREEMENT_WEIGHT,
                      CONF_ANOMALY_WEIGHT, CONF_HIGH, CONF_MARGIN_WEIGHT,
                      CONF_MEDIUM, CV_SCORE_SEVERITY_WEIGHT, DETECT_THRESHOLD,
                      FUSED_SEVERITY_BANDS, ISSUE_CONF_AGREEMENT_WEIGHT,
                      ISSUE_CONF_STRENGTH_WEIGHT, ISSUE_CV_WEIGHT,
                      ISSUE_ML_WEIGHT, ISSUE_TYPES, PIPELINE_VERSION,
                      SCORE_BANDS, SCORE_CV_WEIGHT, SCORE_ML_WEIGHT,
                      STRONG_DISAGREE)
from ..cv.corruption import is_severely_degraded

_SEVERITY_BANDS = FUSED_SEVERITY_BANDS

# key CV metric shown as evidence per issue
_EVIDENCE = {
    "blur": [("laplacian_variance", "sharpness"), ("edge_density", "sharpness")],
    "underexposure": [("mean_luminance", "exposure"), ("dark_fraction", "exposure")],
    "overexposure": [("mean_luminance", "exposure"), ("high_clip_fraction", "exposure")],
    "noise": [("noise_sigma", "noise"), ("hf_residual_std", "noise")],
    "low_contrast": [("percentile_spread", "contrast"), ("rms_contrast", "contrast")],
    "compression": [("blockiness", "compression")],
    "color_cast": [("color_cast", "color"), ("saturation_mean", "color")],
}


def _severity(score: float) -> str:
    for thr, name in _SEVERITY_BANDS:
        if score >= thr:
            return name
    return "LOW"


def _band(score: int) -> str:
    for lo, hi, label in SCORE_BANDS:
        if lo <= score <= hi:
            return label
    return "POTENTIALLY_DEFECTIVE"


def _evidence(issue: str, feats: dict) -> dict:
    out = {}
    for key, group in _EVIDENCE.get(issue, []):
        out[key] = round(float(feats[group][key]), 4)
    return out


def fuse(ml: dict, cv: dict, anomaly: dict) -> dict:
    feats = cv["features"]
    cv_sev = cv["cv_issue_severities"]
    dims = cv["dimensions"]

    issues = []
    agreements = []
    for issue in ISSUE_TYPES:
        ml_p = float(ml["issue_probs"][issue])
        cv_s = float(cv_sev[issue])
        fused = ISSUE_ML_WEIGHT * ml_p + ISSUE_CV_WEIGHT * cv_s
        agreement = 1.0 - abs(ml_p - cv_s)
        agreements.append(agreement)
        detected = fused >= DETECT_THRESHOLD
        # confidence in this specific call: both magnitude and agreement matter
        confidence = round(ISSUE_CONF_AGREEMENT_WEIGHT * agreement
                           + ISSUE_CONF_STRENGTH_WEIGHT * max(ml_p, cv_s), 3)
        issues.append({
            "type": issue,
            "detected": bool(detected),
            "severity": _severity(fused) if detected else "LOW",
            "severity_value": round(fused, 3),
            "confidence": confidence,
            "ml_probability": round(ml_p, 3),
            "cv_severity": round(cv_s, 3),
            "agreement": round(agreement, 3),
            "evidence": _evidence(issue, feats),
        })

    detected_issues = [i for i in issues if i["detected"]]

    # ---- overall quality score: mean of learned and measured scores -------- #
    cv_score = 100.0
    for i in detected_issues:
        cv_score *= (1.0 - CV_SCORE_SEVERITY_WEIGHT * i["cv_severity"])
    quality_score = int(round(SCORE_ML_WEIGHT * ml["model_score"] + SCORE_CV_WEIGHT * cv_score))
    quality_score = max(0, min(100, quality_score))
    quality_label = _band(quality_score)

    # ---- signal agreement -------------------------------------------------- #
    overall_agreement = sum(agreements) / len(agreements)
    agreement_band = "HIGH_AGREEMENT" if overall_agreement >= AGREEMENT_HIGH else "LOW_AGREEMENT"

    # ---- integrity / corruption / severe degradation ---------------------- #
    # Measured from the image (entropy, tonal uniformity, constant rows). This is
    # the classical companion to the anomaly net for gross corruption/degradation
    # that decodes but is clearly broken.
    severely_degraded = is_severely_degraded(feats["integrity"])

    # ---- anomaly conflict -------------------------------------------------- #
    anomaly_detected = anomaly["anomaly_score"] >= ANOMALY_DETECT
    class_margin = max(ml["class_probs"].values()) - sorted(ml["class_probs"].values())[-2]

    # ---- overall confidence ------------------------------------------------ #
    det_agree = (sum(i["agreement"] for i in detected_issues) / len(detected_issues)
                 if detected_issues else overall_agreement)
    anomaly_conflict = 1.0 if (anomaly_detected and ml["quality_class"] == "ACCEPTABLE") else 0.0
    conf_val = round(CONF_AGREEMENT_WEIGHT * det_agree
                     + CONF_MARGIN_WEIGHT * float(class_margin)
                     + CONF_ANOMALY_WEIGHT * (1 - anomaly_conflict), 3)
    if conf_val >= CONF_HIGH:
        confidence_level = "HIGH"
    elif conf_val >= CONF_MEDIUM:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

    # ---- review recommended ----------------------------------------------- #
    review_reasons = []
    if confidence_level == "LOW":
        review_reasons.append("Overall confidence is low.")
    for i in detected_issues:
        if i["agreement"] < STRONG_DISAGREE:
            review_reasons.append(
                f"AI and CV signals disagree on {i['type'].replace('_', ' ')}.")
    if anomaly_conflict:
        review_reasons.append("Autoencoder flags a possible anomaly the classifier missed.")
    if severely_degraded:
        review_reasons.append("Image appears severely degraded or corrupted (very low entropy or constant regions).")
    review_recommended = bool(review_reasons)

    return {
        "pipeline_version": PIPELINE_VERSION,
        "quality_score": quality_score,
        "quality_label": quality_label,
        "quality_class": ml["quality_class"],
        "class_probabilities": {k: round(v, 3) for k, v in ml["class_probs"].items()},
        "overall_confidence": confidence_level,
        "overall_confidence_value": conf_val,
        "review_recommended": review_recommended,
        "review_reasons": review_reasons,
        "issues": issues,
        "detected_issue_types": [i["type"] for i in detected_issues],
        "dimensions": dims,
        "signal_agreement": {
            "overall": agreement_band,
            "value": round(overall_agreement, 3),
            "per_issue": {i["type"]: i["agreement"] for i in issues},
        },
        "anomaly": {
            "detected": bool(anomaly_detected),
            "label": "POTENTIAL_ANOMALY" if anomaly_detected else "NONE",
            # Uncalibrated [0,1] anomaly score (monotonic in the z-score), not a
            # probability. `z_score` is the underlying standardized recon error.
            "score": round(anomaly["anomaly_score"], 3),
            "z_score": round(anomaly["z_score"], 3),
            "recon_error": round(anomaly["recon_error"], 6),
        },
        "integrity": {
            "score": dims["integrity"],                 # 0-100 integrity dimension
            "severely_degraded": bool(severely_degraded),
            "entropy": round(feats["integrity"]["entropy"], 3),
        },
        "model_score": ml["model_score"],
        "cv_score": round(cv_score, 1),
    }
