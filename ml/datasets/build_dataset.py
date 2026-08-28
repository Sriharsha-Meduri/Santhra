"""Build the train/val/test image-quality dataset from clean sources.

CRITICAL - leakage prevention:
The clean *source* images are split FIRST (70/15/15). Only then are degraded
variants generated within each split. No source image (or any of its variants)
can appear in more than one split, so test performance reflects genuine
generalisation to unseen content. A hard assertion enforces this.

Outputs:
    ml/data/dataset/{train,val,test}/*.png   (lossless variants)
    ml/data/manifest.json                     (labels + degradation params)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from degradations import ISSUES, generate_variant  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "ml" / "data"
SRC = DATA / "clean_sources"
OUT = DATA / "dataset"


def _save(img_rgb: np.ndarray, path: Path) -> None:
    cv2.imwrite(str(path), cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))


def build(seed: int, variants: dict[str, int]) -> None:
    sources = sorted(SRC.glob("*.png"))
    if not sources:
        raise SystemExit("No clean sources found. Run prepare_clean_images.py first.")

    rng = np.random.default_rng(seed)
    order = rng.permutation(len(sources))
    n = len(sources)
    n_train, n_val = int(0.70 * n), int(0.15 * n)
    split_idx = {
        "train": order[:n_train],
        "val": order[n_train : n_train + n_val],
        "test": order[n_train + n_val :],
    }

    # leakage guard
    assert set(split_idx["train"]) & set(split_idx["val"]) == set()
    assert set(split_idx["train"]) & set(split_idx["test"]) == set()
    assert set(split_idx["val"]) & set(split_idx["test"]) == set()

    manifest = []
    counts = {s: {"items": 0} for s in split_idx}
    for split, idxs in split_idx.items():
        d = OUT / split
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*.png"):
            f.unlink()
        # Fixed per-split salt so the seed is reproducible across processes.
        # (Python's hash() of a str is randomized by PYTHONHASHSEED, so it must
        # not feed the seed.)
        split_salt = {"train": 0, "val": 1, "test": 2}[split]
        k = 0
        for si in idxs:
            src_path = sources[int(si)]
            clean = cv2.cvtColor(cv2.imread(str(src_path)), cv2.COLOR_BGR2RGB)
            v = variants[split]
            for vi in range(v):
                # independent, reproducible seed per (split, source, variant)
                ss = np.random.SeedSequence([seed, split_salt, int(si), vi])
                r = np.random.default_rng(ss)
                clean_prob = 1.0 if vi == 0 else 0.06   # variant 0 == guaranteed clean
                var = generate_variant(clean, r, clean_prob=clean_prob, max_ops=3)
                fname = f"{split}_{k:05d}.png"
                _save(var.image, d / fname)
                manifest.append({
                    "id": f"{split}_{k:05d}",
                    "split": split,
                    "source_id": src_path.stem,
                    "path": f"dataset/{split}/{fname}",
                    "issue_vector": var.issue_vector,
                    "issues": [i for i in ISSUES if var.issues[i]],
                    "severities": var.severities,
                    "quality_class": var.quality_class,
                    "score": var.score,
                    "params": var.params,
                })
                k += 1
        counts[split]["items"] = k

    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # distribution report
    print("=== dataset built ===")
    for split in ("train", "val", "test"):
        items = [m for m in manifest if m["split"] == split]
        qc = {c: 0 for c in ("ACCEPTABLE", "DEGRADED", "POTENTIALLY_DEFECTIVE")}
        iss = {i: 0 for i in ISSUES}
        for m in items:
            qc[m["quality_class"]] += 1
            for i in m["issues"]:
                iss[i] += 1
        print(f"[{split:5}] sources={len(split_idx[split])} items={len(items)} "
              f"class={qc}")
        print(f"         issues={iss}")
    print(f"manifest -> {DATA / 'manifest.json'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--train-variants", type=int, default=4)
    ap.add_argument("--val-variants", type=int, default=3)
    ap.add_argument("--test-variants", type=int, default=3)
    args = ap.parse_args()
    build(args.seed, {"train": args.train_variants,
                      "val": args.val_variants, "test": args.test_variants})


if __name__ == "__main__":
    main()
