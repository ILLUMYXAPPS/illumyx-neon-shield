"""Tests for the fail-closed application composition boundary."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend.composition import build_service
from backend.managed_store import ManagedAuthStore
from backend.observability import SecurityEvent, SecurityEventSink
from backend.security_monitoring import SecurityAlert, SecurityAlertSink, ProductionSecurityMonitor
from backend.secrets import MappingSecretProvider


class StubManagedStore(ManagedAuthStore):
    def create_user(self, subject_id, identity, credential): pass
    def trust_device(self, subject_id, device_id): pass
    def set_device_trusted(self, subject_id, device_id, trusted): pass
    def block_phone(self, phone): pass
    def find_user(self, identity): return None
    def device_trusted(self, subject_id, device_id): return False
    def device_hash_trusted(self, subject_id, device_hash): return False
    def identity_blocked(self, subject_id): return False
    def phone_blocked(self, phone): return False
    def save_session(self, token, subject_id, device_id, issued_at, expires_at): pass
    def save_session_hash(self, token, subject_id, device_hash, issued_at, expires_at): pass
    def get_session(self, token): return None
    def revoke_session(self, token): pass
    def rotate_session(self, token, new_token, issued_at, expires_at): return None
    def sign_in_rate_limited(self, identity, now, window_seconds, max_sign_ins): return False
    def record_sign_in_failure(self, identity, now, window_seconds, max_sign_ins): pass
    def clear_sign_in_failures(self, identity): pass
    def last_audit_hash(self): return ""
    def add_audit(self, event_type, subject_id, device_id): return ""
    def add_audit_fingerprint(self, event_type, subject_id, device_fingerprint): return ""


class RecordingSink(SecurityEventSink):
    def __init__(self) -> None:
        self.events: list[SecurityEvent] = []

    def emit(self, event: SecurityEvent) -> None:
        self.events.append(event)


class RecordingAlertSink(SecurityAlertSink):
    def __init__(self) -> None:
        self.alerts: list[SecurityAlert] = []

    def emit_alert(self, alert: SecurityAlert) -> None:
        self.alerts.append(alert)


class CompositionTests(unittest.TestCase):
    def _production_env(self):
        return {
            "NEON_AUTH_ENV": "production",
            "NEON_AUTH_DB": "postgresql://managed.example/auth?sslmode=verify-full",
            "NEON_IDP_URL": "https://idp.example",
            "NEON_IDP_CLIENT_ID": "client-id",
            "NEON_MONITORING_ENDPOINT": "https://monitor.example/events",
        }

    def _secret_provider(self):
        return MappingSecretProvider({
            "NEON_IDP_CLIENT_SECRET": "client-secret",
            "NEON_DB_PEPPER": "database-pepper",
        })

    def test_production_requires_secret_provider_injection(self):
        with patch.dict(os.environ, self._production_env(), clear=False):
            with self.assertRaisesRegex(RuntimeError, "injected SecretProvider"):
                build_service()

    def test_production_requires_managed_store_injection(self):
        with patch.dict(os.environ, self._production_env(), clear=False):
            with self.assertRaisesRegex(RuntimeError, "injected ManagedAuthStore"):
                build_service(secret_provider=self._secret_provider())

    def test_production_requires_observability_sink_injection(self):
        store = StubManagedStore()
        with patch.dict(os.environ, self._production_env(), clear=False):
            with self.assertRaisesRegex(RuntimeError, "injected SecurityEventSink"):
                build_service(managed_store=store, secret_provider=self._secret_provider())

    def test_production_requires_alert_sink_injection(self):
        store = StubManagedStore()
        sink = RecordingSink()
        with patch.dict(os.environ, self._production_env(), clear=False):
            with self.assertRaisesRegex(RuntimeError, "injected SecurityAlertSink"):
                build_service(
                    managed_store=store,
                    security_event_sink=sink,
                    secret_provider=self._secret_provider(),
                )

    def test_production_wraps_monitoring_boundary(self):
        store = StubManagedStore()
        sink = RecordingSink()
        alerts = RecordingAlertSink()
        with patch.dict(os.environ, self._production_env(), clear=False):
            service = build_service(
                managed_store=store,
                security_event_sink=sink,
                security_alert_sink=alerts,
                secret_provider=self._secret_provider(),
            )
        self.assertIs(service.store, store)
        self.assertIsInstance(service.security_event_sink, ProductionSecurityMonitor)


if __name__ == "__main__":
    unittest.main()
