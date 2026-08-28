"""Generate a curated, deterministic set of sample images for the repo and the
frontend "Try a sample" demo. Uses fixed (not random) degradations so the demo
is stable across runs.

Base images are the freely-licensed sample photographs bundled with
scikit-image (astronaut: NASA, public domain; rocket: SpaceX, public domain;
chelsea: CC0). They are safe to redistribute in a public repository, unlike the
ImageNet-derived training sources. See sample_images/ATTRIBUTION.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from skimage import data as skdata

REPO = Path(__file__).resolve().parents[1]
SAMPLES = REPO / "sample_images"
FRONTEND = REPO / "frontend" / "public" / "samples"


def _bases() -> list[np.ndarray]:
    """Public-domain / CC0 base photographs (RGB uint8), capped in size."""
    def prep(img: np.ndarray, longest: int = 560) -> np.ndarray:
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        h, w = img.shape[:2]
        sc = longest / max(h, w)
        if sc < 1:
            img = cv2.resize(img, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA)
        return np.ascontiguousarray(img[:, :, :3])
    return [prep(skdata.astronaut()), prep(skdata.chelsea()), prep(skdata.rocket())]


def gblur(img, s):        return cv2.GaussianBlur(img, (0, 0), s)
def bright(img, f):       return np.clip(img.astype(np.float32) * f, 0, 255).astype(np.uint8)
def gnoise(img, std):
    n = np.random.default_rng(0).normal(0, std, img.shape)
    return np.clip(img.astype(np.float32) + n, 0, 255).astype(np.uint8)
def lowcontrast(img, a):
    m = img.reshape(-1, 3).mean(0)
    return np.clip(m + a * (img.astype(np.float32) - m), 0, 255).astype(np.uint8)
def jpeg(img, q):
    ok, enc = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.cvtColor(cv2.imdecode(enc, 1), cv2.COLOR_BGR2RGB)
def anomaly_patch(img):
    """A localized, structurally unnatural corruption (a splice) that the
    clean-image autoencoder cannot reconstruct. Deterministic. Two blocks of
    hard-edged, high-contrast synthetic content that survive the 128px downscale
    and push the reconstruction error well above the clean distribution."""
    out = img.copy().astype(np.uint8)
    h, w = out.shape[:2]
    rng = np.random.default_rng(3)
    # block 1: hard binary random-colour splice (~1/3 of each side)
    ph, pw = h // 3, w // 3
    y, x = h // 5, w // 5
    block = rng.integers(0, 2, (ph, pw, 3), dtype=np.uint8) * 255
    out[y:y + ph, x:x + pw] = block
    # block 2: a flat, fully-saturated magenta bar (colour never seen in nature)
    by, bx = int(h * 0.60), int(w * 0.52)
    bh, bw = h // 5, w // 3
    out[by:by + bh, bx:bx + bw] = (255, 0, 255)
    return out


RECIPES = {
    "clean": lambda im: im,
    "blurry": lambda im: gblur(im, 2.4),
    "severe_blur": lambda im: gblur(im, 5.0),
    "underexposed": lambda im: bright(im, 0.34),
    "overexposed": lambda im: bright(im, 2.2),
    "noisy": lambda im: gnoise(im, 32),
    "compressed": lambda im: jpeg(im, 10),
    "low_contrast": lambda im: lowcontrast(im, 0.32),
    "mixed": lambda im: gnoise(gblur(bright(im, 0.5), 2.0), 22),
    "anomalous": anomaly_patch,
}
# folder mapping (some categories share a folder)
FOLDER = {"clean": "clean", "blurry": "blurry", "severe_blur": "blurry",
          "underexposed": "underexposed", "overexposed": "overexposed",
          "noisy": "noisy", "compressed": "compressed", "low_contrast": "low_contrast",
          "mixed": "mixed", "anomalous": "anomalous"}


def main() -> None:
    bases = _bases()
    for d in set(FOLDER.values()):
        (SAMPLES / d).mkdir(parents=True, exist_ok=True)
    FRONTEND.mkdir(parents=True, exist_ok=True)

    manifest = []
    base = bases[0]                                  # astronaut, scores clean
    for name, fn in RECIPES.items():
        # a couple of variants per category into the repo sample set
        for i, src in enumerate(bases[:2]):
            out = fn(src)
            cv2.imwrite(str(SAMPLES / FOLDER[name] / f"{name}_{i}.png"),
                        cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
        # one representative for the frontend demo
        rep = fn(base)
        fp = FRONTEND / f"{name}.jpg"
        cv2.imwrite(str(fp), cv2.cvtColor(rep, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95])
        manifest.append({"key": name, "label": name.replace("_", " ").title(),
                         "url": f"/samples/{name}.jpg"})
    (FRONTEND / "samples.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[samples] wrote sample_images/ and {len(manifest)} demo samples -> {FRONTEND}")


if __name__ == "__main__":
    main()
