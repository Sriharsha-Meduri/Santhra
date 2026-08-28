"""Structured, dependency-free application logging."""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = (f"{self.formatTime(record, '%Y-%m-%dT%H:%M:%S')} "
                f"{record.levelname:<5} {record.name} :: {record.getMessage()}")
        extras = getattr(record, "context", None)
        if extras:
            base += " | " + " ".join(f"{k}={v}" for k, v in extras.items())
        return base


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(KeyValueFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel("WARNING")
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_context(logger: logging.Logger, level: int, message: str, **context) -> None:
    logger.log(level, message, extra={"context": context})
