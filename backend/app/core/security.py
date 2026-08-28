"""Upload validation & safe decoding.

Never trusts the client. Validates extension + magic bytes, decodes defensively
with OpenCV (Pillow fallback), and rejects anything that will not decode to a
sane RGB image. Filenames are sanitised so nothing is ever written using a
client-controlled path.
"""
from __future__ import annotations

import io
import os
import re

import numpy as np

from ..config import SUPPORTED_FORMATS
from .exceptions import InvalidImageError, UnsupportedFormatError

# magic-byte signatures -> canonical format
_MAGIC = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"BM": "bmp",
    b"II*\x00": "tiff",
    b"MM\x00*": "tiff",
}
_SANE = re.compile(r"[^A-Za-z0-9._-]")
MAX_DIMENSION = 12000
MIN_DIMENSION = 8
# Hard cap on decoded pixel count, checked from the header BEFORE the full
# raster is allocated. Stops a small but highly-compressible file (a
# "decompression bomb") from OOM-killing the worker inside the decoder.
MAX_PIXELS = 50_000_000  # ~50 MP (e.g. 8660x5773); real photos are well under


def sanitize_filename(name: str | None) -> str:
    base = os.path.basename(name or "upload")
    base = _SANE.sub("_", base).strip("._") or "upload"
    return base[:120]


def sniff_format(data: bytes) -> str | None:
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    for sig, fmt in _MAGIC.items():
        if data.startswith(sig):
            return fmt
    return None


def decode_image(data: bytes, declared_ext: str | None = None) -> tuple[np.ndarray, str]:
    """Return (RGB uint8 image, detected_format) or raise a domain error."""
    if not data:
        raise InvalidImageError("Empty file.")
    fmt = sniff_format(data)
    if fmt is None:
        raise UnsupportedFormatError(
            "Unrecognised image content. Supported: " + ", ".join(sorted(SUPPORTED_FORMATS)))
    if fmt not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(f"Unsupported format: {fmt}")

    # Reject oversized geometry from the header before decoding any pixels.
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as probe:
            pw, ph = probe.size
    except Exception:
        pw = ph = 0
    if pw and ph and pw * ph > MAX_PIXELS:
        raise InvalidImageError(f"Image dimensions too large ({pw}x{ph}).")

    import cv2

    rgb: np.ndarray | None = None
    arr = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is not None:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    else:
        try:  # Pillow fallback (webp/tiff edge cases)
            from PIL import Image

            im = Image.open(io.BytesIO(data))
            im.verify()
            im = Image.open(io.BytesIO(data)).convert("RGB")
            rgb = np.asarray(im)
        except Exception as exc:
            raise InvalidImageError(f"Image could not be decoded ({exc}).") from exc

    if rgb is None or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise InvalidImageError("Decoded image is not a valid RGB image.")
    h, w = rgb.shape[:2]
    if h < MIN_DIMENSION or w < MIN_DIMENSION:
        raise InvalidImageError(f"Image too small ({w}x{h}).")
    if h > MAX_DIMENSION or w > MAX_DIMENSION:
        raise InvalidImageError(f"Image too large ({w}x{h}).")
    return np.ascontiguousarray(rgb), fmt
