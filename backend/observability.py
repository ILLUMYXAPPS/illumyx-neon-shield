"""Provider-neutral security observability boundary."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class SecurityEvent:
    """Security event safe for forwarding to a production monitoring provider."""

    name: str
    occurred_at: str
    request_id: str | None = None
    subject_hash: str | None = None
    device_hash: str | None = None
    metadata: Mapping[str, str] | None = None


class SecurityEventSink(ABC):
    """Injected destination for security events; no provider is hard-coded."""

    @abstractmethod
    def emit(self, event: SecurityEvent) -> None:
        """Deliver one security event or raise on delivery failure."""
        raise NotImplementedError


class NoopSecurityEventSink(SecurityEventSink):
    """Development sink that intentionally discards events."""

    def emit(self, event: SecurityEvent) -> None:
        return None


def security_event(
    name: str,
    *,
    request_id: str | None = None,
    subject_hash: str | None = None,
    device_hash: str | None = None,
    metadata: Mapping[str, str] | None = None,
) -> SecurityEvent:
    """Create an event with an explicit UTC timestamp."""
    if not name or name.strip() != name:
        raise ValueError("security event name must be non-empty and trimmed")
    return SecurityEvent(
        name=name,
        occurred_at=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        subject_hash=subject_hash,
        device_hash=device_hash,
        metadata=metadata,
    )
