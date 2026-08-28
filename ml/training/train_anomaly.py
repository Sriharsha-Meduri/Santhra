"""Train the clean-image convolutional autoencoder (anomaly signal).

The AE only ever sees CLEAN (ACCEPTABLE) images from the TRAIN split, so it
learns the "normal" appearance distribution. At inference, a high
reconstruction error on a region/image means it deviates from that learned
normal -> a *potential visual anomaly* (never a confirmed defect). We also
record the clean reconstruction-error distribution to calibrate the anomaly
score at serving time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
import argparse  # noqa: E402
import cv2  # noqa: E402

from app.config import ANOMALY_INPUT_SIZE, CHECKPOINT_DIR  # noqa: E402
from app.ml.model import ConvAutoencoder  # noqa: E402
from app.ml.preprocessing import to_anomaly_tensor  # noqa: E402

DATA = REPO / "ml" / "data"


class CleanSet(Dataset):
    def __init__(self, split: str) -> None:
        man = json.loads((DATA / "manifest.json").read_text())
        self.items = [m for m in man if m["split"] == split
                      and m["quality_class"] == "ACCEPTABLE"]

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int) -> torch.Tensor:
        rgb = cv2.cvtColor(cv2.imread(str(DATA / self.items[i]["path"])), cv2.COLOR_BGR2RGB)
        return to_anomaly_tensor(rgb)


@torch.no_grad()
def recon_errors(model, loader, device) -> np.ndarray:
    model.eval()
    errs = []
    for x in loader:
        x = x.to(device)
        r = model(x)
        errs.append(((r - x) ** 2).mean(dim=(1, 2, 3)).cpu().numpy())
    return np.concatenate(errs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=18)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    args = ap.parse_args()

    torch.manual_seed(0)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tl = DataLoader(CleanSet("train"), batch_size=args.batch_size, shuffle=True, drop_last=True)
    vl = DataLoader(CleanSet("val"), batch_size=args.batch_size)
    print(f"[ae] device={device} clean_train={len(tl.dataset)} clean_val={len(vl.dataset)}")

    model = ConvAutoencoder().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    mse = nn.MSELoss()
    use_amp = device == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    for ep in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for x in tl:
            x = x.to(device)
            opt.zero_grad()
            with torch.autocast(device_type="cuda", enabled=use_amp):
                loss = mse(model(x), x)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            tot += loss.item() * x.size(0)
        if ep % 3 == 0 or ep == args.epochs:
            ve = recon_errors(model, vl, device)
            print(f"[ae ep {ep:02d}] train_mse={tot/len(tl.dataset):.5f} val_recon_mean={ve.mean():.5f}")

    clean_err = recon_errors(model, vl, device)
    stats = {
        "clean_recon_mean": float(clean_err.mean()),
        "clean_recon_std": float(clean_err.std()),
        "clean_recon_p95": float(np.percentile(clean_err, 95)),
        "clean_recon_p99": float(np.percentile(clean_err, 99)),
        "input_size": ANOMALY_INPUT_SIZE,
    }
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": {k: v.cpu() for k, v in model.state_dict().items()}, "stats": stats},
               CHECKPOINT_DIR / "anomaly.pt")
    print(f"[ae] saved -> {CHECKPOINT_DIR/'anomaly.pt'} stats={stats}")


if __name__ == "__main__":
    main()
