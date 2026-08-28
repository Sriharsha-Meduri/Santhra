"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Request

from .db.database import get_db  # re-export for routers

__all__ = ["get_db", "request_id"]


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")
