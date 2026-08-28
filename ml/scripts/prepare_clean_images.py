"""Download a natural-image base set (Imagenette-160) and materialise a folder
of CLEAN source images (lossless PNG, capped resolution) for degradation.

Clean == no *synthetic* degradation. These are real photographs, so they carry
mild native JPEG; the pipeline only ever adds controlled degradations on top,
and the compression class adds heavy JPEG explicitly. Documented in docs/model.md.

Data source: Imagenette (fast.ai), a subset of ImageNet. Used for non-commercial
research/educational purposes under ImageNet's terms; downloaded at build time
and not redistributed with this repo. See docs/model.md (Data, licensing &
attribution).

Run:  python ml/scripts/prepare_clean_images.py --max-sources 1200
"""
from __future__ import annotations

import argparse
import tarfile
import urllib.request
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "ml" / "data"
URL = "https://s3.amazonaws.com/fast-ai-imageclas/imagenette2-160.tgz"


def download_and_extract() -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    tgz = DATA / "imagenette2-160.tgz"
    extracted = DATA / "imagenette2-160"
    if extracted.exists():
        return extracted
    if not tgz.exists():
        print(f"[data] downloading {URL} (~99MB) ...")
        urllib.request.urlretrieve(URL, tgz)
    print("[data] extracting ...")
    with tarfile.open(tgz) as t:
        t.extractall(DATA)
    return extracted


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sources", type=int, default=1200)
    ap.add_argument("--max-side", type=int, default=256)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = download_and_extract()
    imgs = sorted((root / "train").rglob("*.JPEG"))
    print(f"[data] found {len(imgs)} candidate images")
    rng = np.random.default_rng(args.seed)
    idx = rng.permutation(len(imgs))[: args.max_sources]

    out = DATA / "clean_sources"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()

    kept = 0
    for i in sorted(idx):
        bgr = cv2.imread(str(imgs[int(i)]), cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        if min(h, w) < 96:
            continue
        scale = args.max_side / max(h, w)
        if scale < 1.0:
            rgb = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / f"src_{kept:05d}.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        kept += 1
    print(f"[data] wrote {kept} clean source PNGs -> {out}")


if __name__ == "__main__":
    main()
