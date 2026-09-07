"""Contract coverage proving the auth service accepts managed-store adapters."""
from __future__ import annotations

import unittest
from datetime import timedelta

from backend.managed_store import ManagedAuthStore
from backend.service import PersistentIdentityService


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
    def last_audit_hash(self): return ""
    def add_audit(self, event_type, subject_id, device_id): return ""
    def add_audit_fingerprint(self, event_type, subject_id, device_fingerprint): return ""


class ManagedStoreServiceTests(unittest.TestCase):
    def test_service_accepts_managed_store_contract(self):
        store = StubManagedStore()
        service = PersistentIdentityService(store, session_ttl=timedelta(minutes=15))
        self.assertIs(service.store, store)
        self.assertIsInstance(service.store, ManagedAuthStore)


if __name__ == "__main__":
    unittest.main()
