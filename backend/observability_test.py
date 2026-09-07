"""Tests for the provider-neutral security observability boundary."""
from __future__ import annotations

import unittest

from backend.observability import NoopSecurityEventSink, SecurityEventSink, security_event


class RecordingSink(SecurityEventSink):
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


class ObservabilityTests(unittest.TestCase):
    def test_event_has_utc_timestamp_and_safe_fields(self) -> None:
        event = security_event(
            "auth.failure",
            request_id="req-1",
            subject_hash="subject-hash",
            device_hash="device-hash",
            metadata={"reason": "invalid_credentials"},
        )
        self.assertEqual(event.name, "auth.failure")
        self.assertTrue(event.occurred_at.endswith("+00:00"))
        self.assertEqual(event.subject_hash, "subject-hash")
        self.assertNotIn("password", repr(event).lower())

    def test_recording_sink_receives_event(self) -> None:
        sink = RecordingSink()
        event = security_event("session.revoked", request_id="req-2")
        sink.emit(event)
        self.assertEqual(sink.events, [event])

    def test_noop_sink_is_safe_for_development(self) -> None:
        NoopSecurityEventSink().emit(security_event("dev.test"))

    def test_event_name_must_be_trimmed_and_non_empty(self) -> None:
        for name in ("", " auth.failure"):
            with self.assertRaises(ValueError):
                security_event(name)


if __name__ == "__main__":
    unittest.main()
