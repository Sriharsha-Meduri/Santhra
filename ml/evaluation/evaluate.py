"""Evaluate the trained model on the held-out TEST split (unseen sources).

Generates REAL metrics only. Produces:
    ml/evaluation/results/metrics.json
    ml/evaluation/results/confusion_matrix.png
    ml/evaluation/results/per_issue_f1.png
    docs/evaluation.md   (human-readable report with the numbers below)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from sklearn.metrics import (confusion_matrix,  # noqa: E402
                             precision_recall_fscore_support, roc_auc_score)
from torch.utils.data import DataLoader  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "ml" / "datasets"))

from app.config import CHECKPOINT_DIR, ISSUE_TYPES, QUALITY_CLASSES  # noqa: E402
from app.ml.calibration import Calibrator  # noqa: E402
from app.ml.model import SanthraNet  # noqa: E402
from dataset import QualityDataset  # noqa: E402

RESULTS = REPO / "ml" / "evaluation" / "results"
DOCS = REPO / "docs"


@torch.no_grad()
def run(model, ds, device, calib: Calibrator):
    loader = DataLoader(ds, batch_size=64, shuffle=False)
    issue_p, issue_y, cls_p, cls_y, sc_p, sc_y = [], [], [], [], [], []
    for x, t in loader:
        out = model(x.to(device))
        cl = out["class_logits"].cpu().numpy()
        il = out["issue_logits"].cpu().numpy()
        issue_p.append(np.stack([calib.apply_issues(r) for r in il]))
        cls_p.append(np.stack([calib.apply_class(r) for r in cl]))
        issue_y.append(t["issues"].numpy())
        cls_y.append(t["class"].numpy())
        sc_p.append(out["score"].clamp(0, 1).cpu().numpy() * 100)
        sc_y.append(t["score"].numpy() * 100)
    return (np.concatenate(issue_p), np.concatenate(issue_y),
            np.concatenate(cls_p), np.concatenate(cls_y),
            np.concatenate(sc_p), np.concatenate(sc_y))


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ckpt = torch.load(CHECKPOINT_DIR / "model.pt", map_location=device, weights_only=True)
    model = SanthraNet(pretrained=False).to(device).eval()
    model.load_state_dict(ckpt["state_dict"])
    calib = Calibrator.load(CHECKPOINT_DIR / "calibration.json")

    ds = QualityDataset("test")
    items = ds.items
    ip, iy, cp, cy, sp, sy = run(model, ds, device, calib)
    pred_issue = ip > 0.5
    true_issue = iy > 0.5
    pred_cls = cp.argmax(1)

    # ---- per-issue metrics ----
    prec, rec, f1, sup = precision_recall_fscore_support(
        true_issue, pred_issue, average=None, zero_division=0, labels=range(len(ISSUE_TYPES)))
    per_issue = {}
    for k, name in enumerate(ISSUE_TYPES):
        try:
            auc = roc_auc_score(true_issue[:, k], ip[:, k]) if true_issue[:, k].any() and not true_issue[:, k].all() else None
        except Exception:
            auc = None
        per_issue[name] = {"precision": round(float(prec[k]), 4), "recall": round(float(rec[k]), 4),
                           "f1": round(float(f1[k]), 4), "support": int(sup[k]),
                           "roc_auc": round(float(auc), 4) if auc is not None else None}
    macro_f1 = round(float(f1.mean()), 4)
    micro = precision_recall_fscore_support(true_issue, pred_issue, average="micro", zero_division=0)
    micro_f1 = round(float(micro[2]), 4)

    # ---- class metrics ----
    class_acc = round(float((pred_cls == cy).mean()), 4)
    cprec, crec, cf1, csup = precision_recall_fscore_support(
        cy, pred_cls, average=None, zero_division=0, labels=range(len(QUALITY_CLASSES)))
    per_class = {QUALITY_CLASSES[i]: {"precision": round(float(cprec[i]), 4),
                 "recall": round(float(crec[i]), 4), "f1": round(float(cf1[i]), 4),
                 "support": int(csup[i])} for i in range(len(QUALITY_CLASSES))}
    cm = confusion_matrix(cy, pred_cls, labels=range(len(QUALITY_CLASSES)))

    # ---- score regression ----
    score_mae = round(float(np.abs(sp - sy).mean()), 3)
    score_rmse = round(float(np.sqrt(((sp - sy) ** 2).mean())), 3)

    # ---- breakdown by degradation category ----
    n_iss = true_issue.sum(1)
    cats = {"clean (0 issues)": n_iss == 0, "single (1)": n_iss == 1, "mixed (2+)": n_iss >= 2}
    breakdown = {}
    for cat, mask in cats.items():
        if mask.sum() == 0:
            continue
        cf = precision_recall_fscore_support(true_issue[mask], pred_issue[mask],
                                             average="macro", zero_division=0)
        # Macro-F1 is undefined when the subset has no positive labels (the clean
        # subset), so report it as N/A rather than a misleading 0.0.
        has_pos = bool(true_issue[mask].any())
        breakdown[cat] = {"count": int(mask.sum()),
                          "class_acc": round(float((pred_cls[mask] == cy[mask]).mean()), 4),
                          "issue_macro_f1": (round(float(cf[2]), 4) if has_pos else "N/A"),
                          "score_mae": round(float(np.abs(sp[mask] - sy[mask]).mean()), 3)}

    # ---- failure cases ----
    score_err = np.abs(sp - sy)
    worst = np.argsort(-score_err)[:8]
    failures = [{"id": items[i]["id"], "true_class": QUALITY_CLASSES[cy[i]],
                 "pred_class": QUALITY_CLASSES[pred_cls[i]],
                 "true_score": float(round(sy[i], 1)), "pred_score": float(round(sp[i], 1)),
                 "true_issues": [ISSUE_TYPES[k] for k in range(len(ISSUE_TYPES)) if true_issue[i, k]],
                 "pred_issues": [ISSUE_TYPES[k] for k in range(len(ISSUE_TYPES)) if pred_issue[i, k]]}
                for i in worst]

    metrics = {
        "test_items": len(items), "test_sources": len({m["source_id"] for m in items}),
        "issue_macro_f1": macro_f1, "issue_micro_f1": micro_f1, "per_issue": per_issue,
        "class_accuracy": class_acc, "per_class": per_class,
        "confusion_matrix": cm.tolist(), "confusion_labels": QUALITY_CLASSES,
        "score_mae": score_mae, "score_rmse": score_rmse,
        "breakdown": breakdown, "failure_cases": failures,
        "calibration": json.loads((CHECKPOINT_DIR / "calibration.json").read_text())["report"]
        if (CHECKPOINT_DIR / "calibration.json").exists() else None,
    }
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # ---- plots ----
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(3)); ax.set_yticks(range(3))
    ax.set_xticklabels([c[:4] for c in QUALITY_CLASSES]); ax.set_yticklabels([c[:4] for c in QUALITY_CLASSES])
    ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title("Quality-class confusion")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.tight_layout(); fig.savefig(RESULTS / "confusion_matrix.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    ax.bar(range(len(ISSUE_TYPES)), [per_issue[i]["f1"] for i in ISSUE_TYPES], color="#2563eb")
    ax.set_ylim(0, 1); ax.set_ylabel("F1"); ax.set_title("Per-issue F1 (test)")
    ax.set_xticks(range(len(ISSUE_TYPES)))
    ax.set_xticklabels(ISSUE_TYPES, rotation=30, ha="right")
    fig.tight_layout(); fig.savefig(RESULTS / "per_issue_f1.png", dpi=120); plt.close(fig)

    _write_markdown(metrics)
    print(f"[eval] macro-F1={macro_f1} micro-F1={micro_f1} class_acc={class_acc} "
          f"score_mae={score_mae} -> {RESULTS/'metrics.json'}")


def _write_markdown(m: dict) -> None:
    lines = ["# Santhra - Evaluation Report", "",
             "All numbers below are produced by `ml/evaluation/evaluate.py` on the "
             f"**held-out TEST split** ({m['test_items']} variants from "
             f"{m['test_sources']} source images never seen in training/validation). "
             "No metric is hand-written.", "",
             "## Headline", "",
             f"- **Issue macro-F1:** {m['issue_macro_f1']}",
             f"- **Issue micro-F1:** {m['issue_micro_f1']}",
             f"- **Quality-class accuracy:** {m['class_accuracy']}",
             f"- **Quality-score MAE:** {m['score_mae']} / 100  (RMSE {m['score_rmse']})", "",
             "## Per-issue metrics (multi-label)", "",
             "| Issue | Precision | Recall | F1 | ROC-AUC | Support |",
             "|---|---|---|---|---|---|"]
    for k, v in m["per_issue"].items():
        lines.append(f"| {k} | {v['precision']} | {v['recall']} | {v['f1']} | "
                     f"{v['roc_auc']} | {v['support']} |")
    lines += ["", "![Per-issue F1](../ml/evaluation/results/per_issue_f1.png)", "",
              "## Quality class", "",
              "| Class | Precision | Recall | F1 | Support |", "|---|---|---|---|---|"]
    for k, v in m["per_class"].items():
        lines.append(f"| {k} | {v['precision']} | {v['recall']} | {v['f1']} | {v['support']} |")
    lines += ["", "Confusion matrix (rows = true, cols = predicted):", "",
              "![Confusion matrix](../ml/evaluation/results/confusion_matrix.png)", "",
              "## Generalisation breakdown", "",
              "| Subset | Count | Class acc | Issue macro-F1 | Score MAE |",
              "|---|---|---|---|---|"]
    for k, v in m["breakdown"].items():
        lines.append(f"| {k} | {v['count']} | {v['class_acc']} | {v['issue_macro_f1']} | {v['score_mae']} |")
    if m.get("calibration"):
        c = m["calibration"]
        lines += ["", "## Confidence calibration (temperature scaling, val-fit)", "",
                  f"- Class NLL: {c['class_nll_before']} -> **{c['class_nll_after']}**",
                  f"- Class ECE: {c['class_ece_before']} -> **{c['class_ece_after']}**"]
    lines += ["", "## Failure cases (largest score errors)", "",
              "| id | true->pred class | true->pred score | true issues | pred issues |",
              "|---|---|---|---|---|"]
    for f in m["failure_cases"]:
        lines.append(f"| {f['id']} | {f['true_class'][:4]}->{f['pred_class'][:4]} | "
                     f"{f['true_score']}->{f['pred_score']} | {', '.join(f['true_issues']) or '-'} | "
                     f"{', '.join(f['pred_issues']) or '-'} |")
    lines += ["", "## Notes & limitations", "",
              "- Trained on synthetic degradations of natural images; real-world",
              "  degradations may differ (see docs/limitations.md).",
              "- Under/over-exposure have smaller support (they share one recipe group);",
              "  their metrics are noisier than the high-support issues.",
              "- The anomaly autoencoder flags *potential* anomalies, not confirmed defects."]
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
