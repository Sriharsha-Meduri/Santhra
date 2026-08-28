"""Pytest fixtures & helpers. Uses an isolated SQLite DB and the real (committed)
model checkpoints."""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(BACKEND / 'test_santhra.db').as_posix()}")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def _base(h: int = 240, w: int = 320) -> np.ndarray:
    xx, yy = np.meshgrid(np.linspace(0.15, 0.85, w), np.linspace(0.2, 0.8, h))
    img = np.stack([xx, yy, (xx + yy) / 2], axis=2)
    img = (img * 255).astype(np.uint8)
    cv2.circle(img, (w // 3, h // 2), h // 5, (200, 120, 60), -1)
    return cv2.GaussianBlur(img, (0, 0), 1.0)          # smooth, clean-ish


def make_image(kind: str = "clean", fmt: str = ".jpg") -> bytes:
    img = _base()
    if kind == "blurry":
        img = cv2.GaussianBlur(img, (0, 0), 4.5)
    elif kind == "dark":
        img = np.clip(img * 0.3, 0, 255).astype(np.uint8)
    elif kind == "noisy":
        img = np.clip(img + np.random.default_rng(0).normal(0, 35, img.shape), 0, 255).astype(np.uint8)
    params = [cv2.IMWRITE_JPEG_QUALITY, 92] if fmt == ".jpg" else []
    ok, buf = cv2.imencode(fmt, cv2.cvtColor(img, cv2.COLOR_RGB2BGR), params)
    return buf.tobytes()
