"""Shared validation for untrusted metric values used by decision rules."""

from __future__ import annotations

import math
from typing import Any


def finite_number(value: Any) -> float | None:
    """Convert a scalar metric to a finite float; booleans are not numeric metrics."""
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def non_negative_count(value: Any) -> int | None:
    """Return an integral non-negative count, otherwise None."""
    parsed = finite_number(value)
    if parsed is None or parsed < 0 or not parsed.is_integer():
        return None
    return int(parsed)


def percentage(value: Any) -> float | None:
    """Return a finite percentage in the closed interval [0, 100]."""
    parsed = finite_number(value)
    if parsed is None or not 0 <= parsed <= 100:
        return None
    return parsed
