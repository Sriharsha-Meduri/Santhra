"""Post-hoc probability calibration (temperature scaling).

Raw softmax/sigmoid outputs of neural nets are typically over-confident.
Temperature scaling divides logits by a scalar T (fit on the validation set by
minimising NLL) before the softmax/sigmoid, which improves the reliability of
the confidences we surface to the user WITHOUT changing the predicted labels.

We fit one temperature for the 3-way quality-class head and one temperature per
issue for the multi-label head. If no calibration file is present the loader
returns an identity calibrator (T=1), so the system still runs uncalibrated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Calibrator:
    class_temperature: float = 1.0
    issue_temperatures: tuple[float, ...] = ()

    def apply_class(self, logits: np.ndarray) -> np.ndarray:
        z = logits / max(self.class_temperature, 1e-3)
        z = z - z.max()
        e = np.exp(z)
        return e / e.sum()

    def apply_issues(self, logits: np.ndarray) -> np.ndarray:
        t = np.array(self.issue_temperatures) if self.issue_temperatures else np.ones_like(logits)
        t = np.where(t <= 0, 1.0, t)
        return 1.0 / (1.0 + np.exp(-(logits / t)))

    @classmethod
    def load(cls, path: str | Path) -> "Calibrator":
        p = Path(path)
        if not p.exists():
            return cls()
        d = json.loads(p.read_text())
        return cls(
            class_temperature=float(d.get("class_temperature", 1.0)),
            issue_temperatures=tuple(d.get("issue_temperatures", [])),
        )


def fit_temperature(logits: np.ndarray, labels: np.ndarray, multiclass: bool) -> float:
    """1-D temperature search minimising NLL (grid + refine). CPU-only, no torch."""
    labels = np.asarray(labels)
    logits = np.asarray(logits)
    if not multiclass:
        # Binary head: keep logits and labels strictly 1-D so element-wise ops do
        # not broadcast into an (N, N) matrix (which would make the NLL degenerate).
        logits = logits.reshape(-1)
        labels = labels.reshape(-1)

    def nll(t: float) -> float:
        z = logits / t
        if multiclass:
            z = z - z.max(axis=1, keepdims=True)
            p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
            return float(-np.log(p[np.arange(len(labels)), labels] + 1e-12).mean())
        p = 1.0 / (1.0 + np.exp(-z))
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return float(-(labels * np.log(p) + (1 - labels) * np.log(1 - p)).mean())

    grid = np.linspace(0.5, 5.0, 46)
    best = min(grid, key=nll)
    fine = np.linspace(max(0.5, best - 0.1), best + 0.1, 21)
    return float(min(fine, key=nll))


def expected_calibration_error(probs: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    """ECE for binary correctness vs confidence."""
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for i in range(bins):
        m = (probs > edges[i]) & (probs <= edges[i + 1])
        if m.sum() == 0:
            continue
        ece += m.mean() * abs(correct[m].mean() - probs[m].mean())
    return float(ece)
