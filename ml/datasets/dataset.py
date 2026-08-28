"""PyTorch dataset over the generated image-quality manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.config import ISSUE_TYPES, QUALITY_CLASSES  # noqa: E402
from app.ml.preprocessing import to_classifier_tensor  # noqa: E402

DATA = REPO / "ml" / "data"
_CLASS_IDX = {c: i for i, c in enumerate(QUALITY_CLASSES)}


class QualityDataset(Dataset):
    """Returns (image_tensor, {class, issues, score}) for a split.

    Only horizontal flip augmentation is used in training - it is the one
    transform that leaves every quality label (blur/noise/exposure/…) invariant.
    """

    def __init__(self, split: str, augment: bool = False,
                 manifest_path: Path | None = None) -> None:
        man = json.loads((manifest_path or DATA / "manifest.json").read_text())
        self.items = [m for m in man if m["split"] == split]
        self.augment = augment and split == "train"
        if not self.items:
            raise ValueError(f"No items for split={split}")

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, dict]:
        m = self.items[idx]
        bgr = cv2.imread(str(DATA / m["path"]))
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        if self.augment and np.random.rand() < 0.5:
            rgb = np.ascontiguousarray(rgb[:, ::-1])
        x = to_classifier_tensor(rgb)
        target = {
            "class": torch.tensor(_CLASS_IDX[m["quality_class"]], dtype=torch.long),
            "issues": torch.tensor(m["issue_vector"], dtype=torch.float32),
            "score": torch.tensor(m["score"] / 100.0, dtype=torch.float32),
        }
        return x, target


def issue_pos_weights(split: str = "train") -> torch.Tensor:
    """Per-issue positive weights for BCE (counteract class imbalance)."""
    man = json.loads((DATA / "manifest.json").read_text())
    items = [m for m in man if m["split"] == split]
    vecs = np.array([m["issue_vector"] for m in items], dtype=np.float32)
    pos = vecs.sum(axis=0)
    neg = len(items) - pos
    w = np.where(pos > 0, neg / np.maximum(pos, 1.0), 1.0)
    return torch.tensor(np.clip(w, 0.5, 8.0), dtype=torch.float32)
