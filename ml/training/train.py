"""Train the multi-task Santhra classifier.

Losses (combined, documented weights):
    class  : CrossEntropy                        weight 1.0
    issues : BCEWithLogits (pos-weighted)        weight 1.0   (primary objective)
    score  : SmoothL1 on [0,1]                    weight 2.0
The score target lives on [0,1] so its raw gradient is small; upweighting to
2.0 balances it against the classification terms (validated on val set - see
docs/model.md). Issue BCE uses per-class pos-weights to offset imbalance.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "ml" / "datasets"))

from app.config import (CHECKPOINT_DIR, ISSUE_TYPES, MODEL_INPUT_SIZE,  # noqa: E402
                        MODEL_NAME, MODEL_VERSION, QUALITY_CLASSES)
from app.ml.model import build_classifier  # noqa: E402
from dataset import QualityDataset, issue_pos_weights  # noqa: E402

LOSS_WEIGHTS = {"class": 1.0, "issues": 1.0, "score": 2.0}


def seed_all(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


@torch.no_grad()
def evaluate(model, loader, device) -> dict:
    model.eval()
    ys, ps, yc, pc, ysc, psc = [], [], [], [], [], []
    for x, t in loader:
        x = x.to(device)
        out = model(x)
        ps.append(torch.sigmoid(out["issue_logits"]).cpu().numpy())
        ys.append(t["issues"].numpy())
        pc.append(out["class_logits"].argmax(1).cpu().numpy())
        yc.append(t["class"].numpy())
        psc.append(out["score"].cpu().numpy())
        ysc.append(t["score"].numpy())
    P = np.concatenate(ps) > 0.5
    Y = np.concatenate(ys) > 0.5
    macro_f1 = f1_score(Y, P, average="macro", zero_division=0)
    class_acc = float((np.concatenate(pc) == np.concatenate(yc)).mean())
    score_mae = float(np.abs(np.concatenate(psc) - np.concatenate(ysc)).mean() * 100)
    return {"issue_macro_f1": round(macro_f1, 4),
            "class_acc": round(class_acc, 4),
            "score_mae": round(score_mae, 3),
            "selection": round(macro_f1 + class_acc, 4)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=14)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=6e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-pretrained", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="subsample train (smoke test)")
    ap.add_argument("--num-workers", type=int, default=0)
    args = ap.parse_args()

    seed_all(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[train] device={device} pretrained={not args.no_pretrained}")

    train_ds = QualityDataset("train", augment=True)
    val_ds = QualityDataset("val")
    if args.limit:
        train_ds.items = train_ds.items[: args.limit]
    tl = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                    num_workers=args.num_workers, drop_last=True)
    vl = DataLoader(val_ds, batch_size=args.batch_size, num_workers=args.num_workers)
    print(f"[train] train={len(train_ds)} val={len(val_ds)}")

    model = build_classifier(pretrained=not args.no_pretrained).to(device)
    pos_w = issue_pos_weights("train").to(device)
    ce = nn.CrossEntropyLoss()
    bce = nn.BCEWithLogitsLoss(pos_weight=pos_w)
    l1 = nn.SmoothL1Loss()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    use_amp = device == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    best, best_state, bad = -1.0, None, 0
    best_metrics = {}
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    for ep in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        for x, t in tl:
            x = x.to(device)
            yc, yi, ysc = t["class"].to(device), t["issues"].to(device), t["score"].to(device)
            opt.zero_grad()
            with torch.autocast(device_type="cuda", enabled=use_amp):
                out = model(x)
                loss = (LOSS_WEIGHTS["class"] * ce(out["class_logits"], yc)
                        + LOSS_WEIGHTS["issues"] * bce(out["issue_logits"], yi)
                        + LOSS_WEIGHTS["score"] * l1(out["score"], ysc))
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            running += loss.item() * x.size(0)
        sched.step()
        m = evaluate(model, vl, device)
        print(f"[ep {ep:02d}] loss={running/len(train_ds):.4f} "
              f"val_f1={m['issue_macro_f1']} val_acc={m['class_acc']} val_mae={m['score_mae']}")
        if m["selection"] > best:
            best, best_state, best_metrics, bad = m["selection"], \
                {k: v.cpu() for k, v in model.state_dict().items()}, m, 0
        else:
            bad += 1
            if bad >= args.patience:
                print(f"[train] early stop at epoch {ep}")
                break

    ckpt = {
        "state_dict": best_state,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "issue_types": ISSUE_TYPES,
        "quality_classes": QUALITY_CLASSES,
        "input_size": MODEL_INPUT_SIZE,
        "loss_weights": LOSS_WEIGHTS,
        "pretrained_backbone": not args.no_pretrained,
        "framework": f"pytorch-{torch.__version__}",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "val_metrics": best_metrics,
    }
    out = CHECKPOINT_DIR / "model.pt"
    torch.save(ckpt, out)
    (CHECKPOINT_DIR / "train_report.json").write_text(json.dumps(best_metrics, indent=2))
    print(f"[train] best val={best_metrics} -> saved {out}")


if __name__ == "__main__":
    main()
