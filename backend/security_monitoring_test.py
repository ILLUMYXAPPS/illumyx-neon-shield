"""Regression tests for production monitoring and alert routing."""
from __future__ import annotations

import unittest

from backend.observability import SecurityEvent, SecurityEventSink
from backend.security_monitoring import (
    ProductionSecurityMonitor,
    SecurityAlert,
    SecurityAlertSink,
    SecuritySeverity,
    severity_for_event,
    validate_security_event,
)


class RecordingEventSink(SecurityEventSink):
    def __init__(self) -> None:
        self.events: list[SecurityEvent] = []

    def emit(self, event: SecurityEvent) -> None:
        self.events.append(event)


class RecordingAlertSink(SecurityAlertSink):
    def __init__(self) -> None:
        self.alerts: list[SecurityAlert] = []

    def emit_alert(self, alert: SecurityAlert) -> None:
        self.alerts.append(alert)


class SecurityMonitoringTests(unittest.TestCase):
    def _event(self, name: str = "auth.untrusted_device") -> SecurityEvent:
        return SecurityEvent(
            name=name,
            occurred_at="2026-09-07T00:00:00+00:00",
            request_id="req-123",
            subject_hash="a" * 64,
            device_hash="b" * 64,
            metadata={"reason": "device_not_trusted"},
        )

    def test_severity_is_deterministic(self) -> None:
        self.assertEqual(severity_for_event("auth.untrusted_device"), SecuritySeverity.CRITICAL)
        self.assertEqual(severity_for_event("auth.failure"), SecuritySeverity.WARNING)
        self.assertEqual(severity_for_event("session.refreshed"), SecuritySeverity.INFO)

    def test_monitor_forwards_event_and_routes_alert(self) -> None:
        events = RecordingEventSink()
        alerts = RecordingAlertSink()
        monitor = ProductionSecurityMonitor(events, alert_sink=alerts)

        monitor.emit(self._event())

        self.assertEqual(events.events, [self._event()])
        self.assertEqual(len(alerts.alerts), 1)
        self.assertEqual(alerts.alerts[0].severity, SecuritySeverity.CRITICAL)

    def test_info_event_does_not_create_alert(self) -> None:
        events = RecordingEventSink()
        alerts = RecordingAlertSink()
        monitor = ProductionSecurityMonitor(events, alert_sink=alerts)

        monitor.emit(self._event("session.refreshed"))

        self.assertEqual(len(events.events), 1)
        self.assertEqual(alerts.alerts, [])

    def test_rejects_raw_or_unallowlisted_telemetry(self) -> None:
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validate_security_event(
                SecurityEvent(
                    "auth.failure",
                    "2026-09-07T00:00:00+00:00",
                    subject_hash="raw-email@example.com",
                )
            )

        with self.assertRaisesRegex(ValueError, "not allowlisted"):
            validate_security_event(
                SecurityEvent(
                    "auth.failure",
                    "2026-09-07T00:00:00+00:00",
                    metadata={"password": "never-log-this"},
                )
            )

    def test_delivery_failures_propagate(self) -> None:
        class FailingSink(SecurityEventSink):
            def emit(self, event: SecurityEvent) -> None:
                raise RuntimeError("monitoring delivery failed")

        monitor = ProductionSecurityMonitor(FailingSink())
        with self.assertRaisesRegex(RuntimeError, "monitoring delivery failed"):
            monitor.emit(self._event())


if __name__ == "__main__":
    unittest.main()
