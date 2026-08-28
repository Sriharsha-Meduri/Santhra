"""Fit temperature-scaling calibration on the validation set.

Produces ml/checkpoints/calibration.json with a temperature for the quality
class head and one per issue, plus a before/after reliability report (NLL/ECE)
that is quoted in docs/evaluation.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "ml" / "datasets"))

from app.config import CHECKPOINT_DIR, ISSUE_TYPES  # noqa: E402
from app.ml.calibration import (expected_calibration_error,  # noqa: E402
                                fit_temperature)
from app.ml.model import SanthraNet  # noqa: E402
from dataset import QualityDataset  # noqa: E402


@torch.no_grad()
def collect(model, loader, device):
    cl, il, yc, yi = [], [], [], []
    for x, t in loader:
        out = model(x.to(device))
        cl.append(out["class_logits"].cpu().numpy())
        il.append(out["issue_logits"].cpu().numpy())
        yc.append(t["class"].numpy())
        yi.append(t["issues"].numpy())
    return (np.concatenate(cl), np.concatenate(il),
            np.concatenate(yc), np.concatenate(yi))


def _nll_multiclass(logits, labels, t=1.0):
    z = logits / t
    z = z - z.max(1, keepdims=True)
    p = np.exp(z) / np.exp(z).sum(1, keepdims=True)
    return float(-np.log(p[np.arange(len(labels)), labels] + 1e-12).mean())


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ckpt = torch.load(CHECKPOINT_DIR / "model.pt", map_location=device, weights_only=True)
    model = SanthraNet(pretrained=False).to(device).eval()
    model.load_state_dict(ckpt["state_dict"])
    vl = DataLoader(QualityDataset("val"), batch_size=64)
    cl, il, yc, yi = collect(model, vl, device)

    class_T = fit_temperature(cl, yc, multiclass=True)
    issue_T = [fit_temperature(il[:, k], yi[:, k], multiclass=False)
               for k in range(len(ISSUE_TYPES))]

    # reliability report
    conf_before = np.exp(cl - cl.max(1, keepdims=True))
    conf_before = (conf_before / conf_before.sum(1, keepdims=True)).max(1)
    correct = (cl.argmax(1) == yc).astype(float)
    z = cl / class_T
    conf_after = np.exp(z - z.max(1, keepdims=True))
    conf_after = (conf_after / conf_after.sum(1, keepdims=True)).max(1)

    report = {
        "class_nll_before": round(_nll_multiclass(cl, yc, 1.0), 4),
        "class_nll_after": round(_nll_multiclass(cl, yc, class_T), 4),
        "class_ece_before": round(expected_calibration_error(conf_before, correct), 4),
        "class_ece_after": round(expected_calibration_error(conf_after, correct), 4),
    }
    out = {
        "class_temperature": round(class_T, 4),
        "issue_temperatures": [round(t, 4) for t in issue_T],
        "issue_names": ISSUE_TYPES,
        "report": report,
        "method": "temperature scaling (val-fit, NLL objective)",
    }
    (CHECKPOINT_DIR / "calibration.json").write_text(json.dumps(out, indent=2))
    print("calibration:", json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
