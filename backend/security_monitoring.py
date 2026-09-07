"""Provider-neutral monitoring and alert-routing hardening.

This module validates security telemetry before it crosses the production
monitoring boundary and routes high-risk events to an injected alert sink.
No provider, credentials, network client, or secret material is embedded.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import re

from backend.observability import SecurityEvent, SecurityEventSink


class SecuritySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class SecurityAlert:
    event: SecurityEvent
    severity: SecuritySeverity


class SecurityAlertSink(ABC):
    """Injected destination for actionable security alerts."""

    @abstractmethod
    def emit_alert(self, alert: SecurityAlert) -> None:
        """Deliver an alert or raise on delivery failure."""
        raise NotImplementedError


class NoopSecurityAlertSink(SecurityAlertSink):
    """Development alert sink that intentionally discards alerts."""

    def emit_alert(self, alert: SecurityAlert) -> None:
        return None


_CRITICAL_EVENTS = frozenset(
    {
        "auth.blocked_identity",
        "auth.blocked_phone",
        "auth.untrusted_device",
        "auth.rate_limited",
        "session.blocked_identity",
        "session.untrusted_device",
    }
)
_WARNING_EVENTS = frozenset({"auth.failure", "session.invalid", "session.rejected", "session.expired"})
_ALLOWED_METADATA_KEYS = frozenset({"reason", "event"})
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def severity_for_event(name: str) -> SecuritySeverity:
    """Return the deterministic severity used by production alert routing."""
    if name in _CRITICAL_EVENTS:
        return SecuritySeverity.CRITICAL
    if name in _WARNING_EVENTS:
        return SecuritySeverity.WARNING
    return SecuritySeverity.INFO


def validate_security_event(event: SecurityEvent) -> None:
    """Reject telemetry that could violate the production privacy boundary."""
    if not event.name or event.name != event.name.strip():
        raise ValueError("security event name must be non-empty and trimmed")
    if not (event.name.startswith("auth.") or event.name.startswith("session.")):
        raise ValueError("unsupported security event name")
    if event.request_id is not None and (not event.request_id.strip() or len(event.request_id) > 128):
        raise ValueError("request_id must be non-empty and at most 128 characters")
    for field_name, value in (("subject_hash", event.subject_hash), ("device_hash", event.device_hash)):
        if value is not None and not _HASH_RE.fullmatch(value):
            raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    if event.metadata is not None:
        for key, value in event.metadata.items():
            if key not in _ALLOWED_METADATA_KEYS:
                raise ValueError(f"metadata key is not allowlisted: {key}")
            if not isinstance(value, str) or not value.strip() or len(value) > 128:
                raise ValueError("metadata values must be non-empty strings of at most 128 characters")


class ProductionSecurityMonitor(SecurityEventSink):
    """Validate, forward, and alert on application security events."""

    def __init__(
        self,
        event_sink: SecurityEventSink,
        *,
        alert_sink: SecurityAlertSink | None = None,
    ) -> None:
        self._event_sink = event_sink
        self._alert_sink = alert_sink or NoopSecurityAlertSink()

    def emit(self, event: SecurityEvent) -> None:
        validate_security_event(event)
        self._event_sink.emit(event)
        severity = severity_for_event(event.name)
        if severity is not SecuritySeverity.INFO:
            self._alert_sink.emit_alert(SecurityAlert(event, severity))
