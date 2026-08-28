"""Explainability: heatmaps, problem-region overlays, Quality Forensics.

Everything here is derived from real signals:
* the AI heatmap is a genuine Grad-CAM on the learned model's quality decision;
* the problem-region overlay is a real CV map (weak-gradient / clipping / noise)
  or the autoencoder residual for anomalies.
No decorative or synthetic heatmaps are ever produced.
"""
from __future__ import annotations

import base64

import cv2
import numpy as np

from ..config import QUALITY_CLASSES
from ..core.logging import get_logger
from ..cv.anomaly import anomaly_map
from ..cv.exposure import clipping_map
from ..cv.noise import noise_map
from ..cv.sharpness import local_sharpness_map
from ..cv.utils import resize_max_side

_FORENSIC_TEXT = {
    "blur": ("Sharpness anomaly", "laplacian_variance", "sharpness",
             "Healthy images in this distribution show substantially stronger edge response."),
    "underexposure": ("Exposure deficit", "mean_luminance", "exposure",
                      "Well-exposed images sit around mid-luminance; this one is far darker."),
    "overexposure": ("Highlight clipping", "high_clip_fraction", "exposure",
                     "Well-exposed images retain highlight detail; large clipped areas indicate over-exposure."),
    "noise": ("High-frequency noise", "noise_sigma", "noise",
              "Clean images have low residual noise; the estimated sigma here is elevated."),
    "low_contrast": ("Compressed tonal range", "percentile_spread", "contrast",
                     "Healthy images use a wide tonal range; this one is tonally flat."),
    "compression": ("Block artifacts", "blockiness", "compression",
                    "Clean images show no 8x8 block structure; measured blockiness is high."),
    "color_cast": ("Colour abnormality", "color_cast", "color",
                   "Neutral images have near-zero global colour cast; a tint is present here."),
}


def _overlay(image_rgb: np.ndarray, heat01: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    heat = (np.clip(heat01, 0, 1) * 255).astype(np.uint8)
    heat = cv2.resize(heat, (image_rgb.shape[1], image_rgb.shape[0]))
    color = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
    color = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
    return cv2.addWeighted(image_rgb, 1 - alpha, color, alpha, 0)


def _data_url(image_rgb: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
    b64 = base64.b64encode(buf).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _problem_map(primary: str | None, image_rgb: np.ndarray,
                 anomaly_residual: np.ndarray | None) -> tuple[np.ndarray, str]:
    if primary in ("blur",):
        return local_sharpness_map(image_rgb), "weak-gradient (blur) regions"
    if primary in ("underexposure", "overexposure"):
        return clipping_map(image_rgb), "clipped shadow/highlight regions"
    if primary == "noise":
        return noise_map(image_rgb), "high-frequency (noise) regions"
    if anomaly_residual is not None:
        res = cv2.resize(anomaly_residual, (image_rgb.shape[1], image_rgb.shape[0]))
        return anomaly_map(res), "autoencoder anomaly residual"
    # fallback: inverse sharpness
    return local_sharpness_map(image_rgb), "low-detail regions"


def build_explainability(image_rgb: np.ndarray, features: dict, fusion: dict,
                         anomaly: dict, engine) -> dict:
    img = resize_max_side(image_rgb)
    feats = features["features"]
    detected = [i for i in fusion["issues"] if i["detected"]]
    detected.sort(key=lambda x: x["severity_value"], reverse=True)
    primary = detected[0]["type"] if detected else None

    # AI heatmap: Grad-CAM on the predicted quality class
    heatmap_url, heatmap_method = None, "unavailable"
    if engine.model_loaded:
        try:
            cls_idx = QUALITY_CLASSES.index(fusion["quality_class"])
            cam = engine.grad_cam(img, cls_idx, head="class")
            heatmap_url = _data_url(_overlay(img, cam))
            heatmap_method = "Grad-CAM (quality-class head)"
        except Exception as exc:  # pragma: no cover
            get_logger("santhra.explain").warning("grad-cam failed: %r", exc)
            heatmap_method = "unavailable"

    # problem-region overlay from CV / anomaly
    pmap, pmethod = _problem_map(primary, img, anomaly.get("_residual_map"))
    problem_url = _data_url(_overlay(img, pmap, alpha=0.5))

    # Quality Forensics cards
    forensics = []
    for i in detected[:4]:
        sig, key, group, expectation = _FORENSIC_TEXT[i["type"]]
        forensics.append({
            "issue": i["type"],
            "signal": sig,
            "observed": f"{key} = {round(float(feats[group][key]), 3)}",
            "model_expectation": expectation,
            "assessment": f"Likely {i['type'].replace('_', ' ')} ({i['severity'].lower()})",
            "confidence": round(i["confidence"] * 100),
        })

    # concise evidence cards + narrative
    evidence_cards, narrative_parts = [], []
    rank = ["Primary", "Secondary", "Additional", "Additional"]
    for n, i in enumerate(detected[:4]):
        ev = ", ".join(f"{k}={v}" for k, v in i["evidence"].items())
        evidence_cards.append({
            "issue": i["type"],
            "severity": i["severity"],
            "confidence": round(i["confidence"] * 100),
            "explanation": f"AI probability {round(i['ml_probability']*100)}% and CV severity "
                           f"{round(i['cv_severity']*100)}% both indicate {i['type'].replace('_',' ')}.",
            "statistic": ev,
        })
        label = rank[n] if n < len(rank) else "Additional"
        narrative_parts.append(
            f"{label} issue: {i['type'].replace('_',' ')} ({i['severity']}). {ev}.")
    if not detected:
        narrative_parts.append("No quality issues detected; measured signals and the "
                                "learned model both indicate an acceptable image.")

    return {
        "primary_issue": primary,
        "heatmap": heatmap_url,
        "heatmap_method": heatmap_method,
        "problem_regions": problem_url,
        "problem_method": pmethod,
        "forensics": forensics,
        "evidence_cards": evidence_cards,
        "narrative": " ".join(narrative_parts),
    }
