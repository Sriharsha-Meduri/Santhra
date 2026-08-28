"""Time helpers.

SQLite does not preserve tzinfo on DateTime columns, so values written as
timezone-aware UTC read back naive. `iso_utc` normalises either form to an
unambiguous UTC ISO-8601 string with a trailing ``Z`` so the browser's
``new Date(...)`` parses the correct instant instead of assuming local time.
"""
from __future__ import annotations

from datetime import datetime, timezone


def iso_utc(dt: datetime) -> str:
    """Return an ISO-8601 UTC string ending in ``Z``.

    A naive datetime is assumed to already be UTC (that is how we store it).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
