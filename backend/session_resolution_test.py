"""Regression coverage for the production session resolution boundary."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from auth_server_contract import AuthFailure
from auth_server import AuthenticationError
from backend.service import PersistentIdentityService
from backend.managed_store import ManagedAuthStore


class StubManagedStore(ManagedAuthStore):
    def __init__(self):
        self.row = None
        self.trusted = True

    def create_user(self, subject_id, identity, credential): pass
    def trust_device(self, subject_id, device_id): pass
    def set_device_trusted(self, subject_id, device_id, trusted): pass
    def block_phone(self, phone): pass
    def find_user(self, identity): return None
    def device_trusted(self, subject_id, device_id): return self.trusted
    def device_hash_trusted(self, subject_id, device_hash): return self.trusted
    def identity_blocked(self, subject_id): return False
    def phone_blocked(self, phone): return False
    def save_session(self, token, subject_id, device_id, issued_at, expires_at): pass
    def save_session_hash(self, token, subject_id, device_hash, issued_at, expires_at): pass
    def get_session(self, token): return self.row
    def revoke_session(self, token): pass
    def rotate_session(self, token, new_token, issued_at, expires_at): return None
    def sign_in_rate_limited(self, identity, now, window_seconds, max_sign_ins): return False
    def record_sign_in_failure(self, identity, now, window_seconds, max_sign_ins): pass
    def reserve_sign_in_attempt(self, identity, now, window_seconds, max_sign_ins): return True
    def clear_sign_in_failures(self, identity): pass
    def last_audit_hash(self): return ""
    def add_audit(self, event_type, subject_id, device_id): return ""
    def add_audit_fingerprint(self, event_type, subject_id, device_fingerprint): return ""


class SessionResolutionTests(unittest.TestCase):
    def test_resolve_session_returns_authoritative_session(self):
        store = StubManagedStore()
        issued = datetime.now(timezone.utc) - timedelta(minutes=1)
        expires = datetime.now(timezone.utc) + timedelta(minutes=14)
        store.row = {
            "subject_id": "subject-1",
            "device_hash": "a" * 64,
            "issued_at": issued.isoformat(),
            "expires_at": expires.isoformat(),
            "revoked": False,
        }
        service = PersistentIdentityService(store)
        session = service.resolve_session("token-1")
        self.assertEqual(session.session_id, "token-1")
        self.assertEqual(session.subject_id, "subject-1")
        self.assertEqual(session.device_id, "a" * 64)
        self.assertEqual(session.issued_at, issued)
        self.assertEqual(session.expires_at, expires)

    def test_resolve_session_rejects_untrusted_device(self):
        store = StubManagedStore()
        store.trusted = False
        store.row = {
            "subject_id": "subject-1",
            "device_hash": "a" * 64,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=14)).isoformat(),
            "revoked": False,
        }
        service = PersistentIdentityService(store)
        with self.assertRaises(AuthenticationError) as raised:
            service.resolve_session("token-1")
        self.assertEqual(raised.exception.failure, AuthFailure.UNTRUSTED_DEVICE)


if __name__ == "__main__":
    unittest.main()
