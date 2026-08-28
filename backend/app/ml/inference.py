"""Inference engine: loads the learned models ONCE and serves predictions.

Provides:
* ``predict``   - calibrated class probs, multi-label issue probs, 0-100 score.
* ``anomaly``   - AE reconstruction residual map + uncalibrated anomaly score.
* ``grad_cam``  - class-activation heatmap for a chosen class/issue logit.
"""
from __future__ import annotations

import threading
from pathlib import Path

import cv2
import numpy as np
import torch

from ..config import (ANOMALY_SIGMOID_CENTER, ISSUE_TYPES, QUALITY_CLASSES,
                      get_settings, resolve_device)
from ..cv.anomaly import anomaly_map, reconstruction_residual, summarize
from .calibration import Calibrator
from .model import ConvAutoencoder, SanthraNet
from .preprocessing import (anomaly_tensor_to_rgb01, to_anomaly_tensor,
                            to_classifier_tensor)


class InferenceEngine:
    """Thread-safe-enough singleton wrapper around the two learned models."""

    def __init__(self, model_path: str, anomaly_path: str, calibration_path: str,
                 device: str | None = None) -> None:
        self.device = resolve_device(device)
        self.model_loaded = False
        self.anomaly_loaded = False
        self.meta: dict = {"model_name": "uninitialised", "model_version": "0"}

        self.model = SanthraNet(pretrained=False).to(self.device).eval()
        if Path(model_path).exists():
            ckpt = torch.load(model_path, map_location=self.device, weights_only=True)
            # Guard against a silent label reordering: the checkpoint's head order
            # must match the live config, or every prediction would be mislabelled.
            ck_issues = list(ckpt.get("issue_types", ISSUE_TYPES))
            ck_classes = list(ckpt.get("quality_classes", QUALITY_CLASSES))
            if ck_issues != list(ISSUE_TYPES) or ck_classes != list(QUALITY_CLASSES):
                raise RuntimeError(
                    "Checkpoint label order does not match config: "
                    f"issues {ck_issues} vs {list(ISSUE_TYPES)}; "
                    f"classes {ck_classes} vs {list(QUALITY_CLASSES)}")
            self.model.load_state_dict(ckpt["state_dict"])
            self.meta = {k: v for k, v in ckpt.items() if k != "state_dict"}
            self.model_loaded = True

        self.ae = ConvAutoencoder().to(self.device).eval()
        self.ae_stats = {"clean_recon_mean": 0.0, "clean_recon_std": 1.0,
                         "clean_recon_p95": 1.0, "clean_recon_p99": 1.0}
        if Path(anomaly_path).exists():
            a = torch.load(anomaly_path, map_location=self.device, weights_only=True)
            self.ae.load_state_dict(a["state_dict"])
            self.ae_stats = a.get("stats", self.ae_stats)
            self.anomaly_loaded = True

        self.calibrator = Calibrator.load(calibration_path)
        # Serialises all access to the shared model/AE. grad_cam runs a backward
        # pass and mutates module hooks/grads, so concurrent requests (now run in
        # a threadpool) must not touch the model at the same time.
        self.lock = threading.Lock()

    # ------------------------------------------------------------------ #
    @torch.inference_mode()
    def predict(self, image_rgb: np.ndarray) -> dict:
        with self.lock:
            x = to_classifier_tensor(image_rgb).unsqueeze(0).to(self.device)
            out = self.model(x)
            class_logits = out["class_logits"][0].float().cpu().numpy()
            issue_logits = out["issue_logits"][0].float().cpu().numpy()
            score = float(out["score"][0].clamp(0, 1).cpu().numpy()) * 100.0

        class_probs = self.calibrator.apply_class(class_logits)
        issue_probs = self.calibrator.apply_issues(issue_logits)
        cls_idx = int(class_probs.argmax())
        return {
            "quality_class": QUALITY_CLASSES[cls_idx],
            "class_probs": {c: float(class_probs[i]) for i, c in enumerate(QUALITY_CLASSES)},
            "issue_probs": {t: float(issue_probs[i]) for i, t in enumerate(ISSUE_TYPES)},
            "model_score": round(score, 1),
        }

    # ------------------------------------------------------------------ #
    @torch.inference_mode()
    def anomaly(self, image_rgb: np.ndarray) -> dict:
        with self.lock:
            x = to_anomaly_tensor(image_rgb).unsqueeze(0).to(self.device)
            recon = self.ae(x)
        err = float(((recon - x) ** 2).mean().cpu().numpy())
        orig01 = anomaly_tensor_to_rgb01(x[0])
        recon01 = anomaly_tensor_to_rgb01(recon[0])
        residual = reconstruction_residual(orig01, recon01)
        # Standardise the reconstruction error against the clean-image
        # distribution (mean/std fit on clean val images). `z` is a real z-score;
        # `anomaly_score` is a bounded [0,1] MONOTONIC transform of it (a sigmoid
        # centred at ~2 sigma) for display. It is NOT a calibrated probability
        # (there is no anomaly-labelled data to calibrate against) - it just
        # ranks how far above normal the reconstruction error is.
        mean, std = self.ae_stats["clean_recon_mean"], max(self.ae_stats["clean_recon_std"], 1e-6)
        z = (err - mean) / std
        score = float(1.0 / (1.0 + np.exp(-(z - ANOMALY_SIGMOID_CENTER))))
        return {
            "recon_error": err,
            "z_score": float(z),
            "anomaly_score": score,
            **summarize(residual),
            "_residual_map": residual,           # 128x128, used by explainability
        }

    # ------------------------------------------------------------------ #
    def grad_cam(self, image_rgb: np.ndarray, class_idx: int,
                 head: str = "class") -> np.ndarray:
        """Grad-CAM heatmap (H,W in [0,1]) for a class or issue logit."""
        acts: list[torch.Tensor] = []
        grads: list[torch.Tensor] = []
        with self.lock:
            target = self.model.gradcam_target
            h1 = target.register_forward_hook(lambda m, i, o: acts.append(o))
            h2 = target.register_full_backward_hook(lambda m, gi, go: grads.append(go[0]))
            try:
                x = to_classifier_tensor(image_rgb).unsqueeze(0).to(self.device)
                self.model.zero_grad(set_to_none=True)
                out = self.model(x)
                logit = out["issue_logits" if head == "issue" else "class_logits"][0, class_idx]
                logit.backward()
                A = acts[-1].detach()[0]                     # (C,h,w)
                G = grads[-1].detach()[0]                     # (C,h,w)
                weights = G.mean(dim=(1, 2))                  # GAP over spatial
                cam = torch.relu((weights[:, None, None] * A).sum(0))
                cam = cam.cpu().numpy()
            finally:
                h1.remove()
                h2.remove()
        if cam.max() - cam.min() < 1e-8:
            cam = np.zeros_like(cam)
        else:
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        return cv2.resize(cam, (image_rgb.shape[1], image_rgb.shape[0]))
