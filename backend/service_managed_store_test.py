"""Contract coverage for managed stores and security observability injection."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, ServerSession, SignInRequest
from backend.managed_store import ManagedAuthStore
from backend.observability import SecurityEvent, SecurityEventSink
from backend.service import PersistentIdentityService
from backend.store import AuthStore


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
    def last_audit_hash(self): return ""
    def add_audit(self, event_type, subject_id, device_id): return ""
    def add_audit_fingerprint(self, event_type, subject_id, device_fingerprint): return ""


class RecordingSink(SecurityEventSink):
    def __init__(self) -> None:
        self.events: list[SecurityEvent] = []

    def emit(self, event: SecurityEvent) -> None:
        self.events.append(event)


class ManagedStoreServiceTests(unittest.TestCase):
    def test_service_accepts_managed_store_contract(self):
        store = StubManagedStore()
        service = PersistentIdentityService(store, session_ttl=timedelta(minutes=15))
        self.assertIs(service.store, store)
        self.assertIsInstance(service.store, ManagedAuthStore)

    def test_service_emits_safe_event_for_invalid_sign_in(self):
        store = StubManagedStore()
        sink = RecordingSink()
        service = PersistentIdentityService(store, security_event_sink=sink)

        with self.assertRaises(AuthenticationError) as raised:
            service.sign_in(SignInRequest("", "credential-is-never-logged", "device-123"))

        self.assertEqual(raised.exception.failure, AuthFailure.INVALID_CREDENTIALS)
        self.assertEqual(len(sink.events), 1)
        event = sink.events[0]
        self.assertEqual(event.name, "auth.failure")
        self.assertEqual(event.metadata, {"reason": "invalid_request"})
        self.assertIsNone(event.subject_hash)
        self.assertIsNone(event.device_hash)

    def test_sqlite_rotation_consumes_old_session_once(self):
        store = AuthStore(":memory:", pepper="test-pepper")
        now = datetime.now(timezone.utc)
        store.save_session("old", "subject-1", "device-1", now.isoformat(), (now + timedelta(minutes=15)).isoformat())
        first = store.rotate_session("old", "new-1", now.isoformat(), (now + timedelta(minutes=15)).isoformat())
        second = store.rotate_session("old", "new-2", now.isoformat(), (now + timedelta(minutes=15)).isoformat())

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertIsNotNone(store.get_session("new-1"))
        self.assertIsNone(store.get_session("new-2"))
        self.assertTrue(store.get_session("old")["revoked"])
        store.close()


if __name__ == "__main__":
    unittest.main()
