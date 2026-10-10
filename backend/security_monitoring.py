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
_WARNING_EVENTS = frozenset(
    {"auth.failure", "session.invalid", "session.rejected", "session.expired"}
)
_INFO_EVENTS = frozenset(
    {"auth.success", "session.created", "session.refreshed", "session.revoked"}
)
_ALLOWED_METADATA_KEYS = frozenset({"reason", "event"})
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def severity_for_event(name: str) -> SecuritySeverity:
    """Return severity; unknown names fail toward warning, never silent info."""
    if name in _CRITICAL_EVENTS:
        return SecuritySeverity.CRITICAL
    if name in _WARNING_EVENTS:
        return SecuritySeverity.WARNING
    if name in _INFO_EVENTS:
        return SecuritySeverity.INFO
    # New or misspelled auth/session events should be visible until classified.
    if isinstance(name, str) and (name.startswith("auth.") or name.startswith("session.")):
        return SecuritySeverity.WARNING
    raise ValueError("unsupported security event name")


def validate_security_event(event: SecurityEvent) -> None:
    """Reject telemetry that could violate the production privacy boundary."""
    if not isinstance(event.name, str) or not event.name or event.name != event.name.strip():
        raise ValueError("security event name must be a non-empty trimmed string")
    if not (event.name.startswith("auth.") or event.name.startswith("session.")):
        raise ValueError("unsupported security event name")
    if event.request_id is not None:
        if not isinstance(event.request_id, str) or not event.request_id.strip() or len(event.request_id) > 128:
            raise ValueError("request_id must be a non-empty string of at most 128 characters")
    for field_name, value in (("subject_hash", event.subject_hash), ("device_hash", event.device_hash)):
        if value is not None and (not isinstance(value, str) or not _HASH_RE.fullmatch(value)):
            raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    if event.metadata is not None:
        if not isinstance(event.metadata, dict):
            raise ValueError("metadata must be a dictionary")
        for key, value in event.metadata.items():
            if not isinstance(key, str) or key not in _ALLOWED_METADATA_KEYS:
                raise ValueError("metadata key is not allowlisted")
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
        if event_sink is None:
            raise ValueError("event_sink is required")
        self._event_sink = event_sink
        self._alert_sink = alert_sink if alert_sink is not None else NoopSecurityAlertSink()

    def emit(self, event: SecurityEvent) -> None:
        validate_security_event(event)
        self._event_sink.emit(event)
        severity = severity_for_event(event.name)
        if severity is not SecuritySeverity.INFO:
            self._alert_sink.emit_alert(SecurityAlert(event, severity))
