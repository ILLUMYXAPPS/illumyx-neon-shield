"""Provider-neutral distributed sign-in rate-limit validation."""
from __future__ import annotations

from datetime import datetime


def validate_rate_limit_window(window_seconds: int) -> None:
    if window_seconds < 1:
        raise ValueError("rate-limit window must be positive")


def validate_rate_limit_threshold(max_sign_ins: int) -> None:
    if max_sign_ins < 1:
        raise ValueError("rate-limit threshold must be positive")


def normalize_rate_limit_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("rate-limit timestamps must be timezone-aware")
    return parsed.isoformat()
