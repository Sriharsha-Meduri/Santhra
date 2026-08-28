"""Process-wide singleton for the learned models (loaded once)."""
from __future__ import annotations

import threading

from ..config import get_settings
from ..ml.inference import InferenceEngine

_engine: InferenceEngine | None = None
_lock = threading.Lock()


def get_engine() -> InferenceEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                s = get_settings()
                _engine = InferenceEngine(
                    s.model_path, s.anomaly_model_path, s.calibration_path
                )
    return _engine
