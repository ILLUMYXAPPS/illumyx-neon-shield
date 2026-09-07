"""Focused regression tests for the DB-API managed auth adapter."""
from __future__ import annotations

import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.managed_db_store import ManagedDbAuthStore
from backend.managed_store import ManagedAuthStore


def _store(tmp: Path) -> ManagedDbAuthStore:
    path = tmp / "managed-test.sqlite3"
    return ManagedDbAuthStore(lambda: sqlite3.connect(path), pepper="test-pepper", placeholder="?", audit_lock_clause="")


class ManagedDbAuthStoreTests(unittest.TestCase):
    def test_defaults_to_row_locking_for_managed_database(self) -> None:
        store = ManagedDbAuthStore(lambda: sqlite3.connect(":memory:"), pepper="test-pepper", placeholder="?")
        self.assertEqual(store._audit_lock_clause, " FOR UPDATE")

    def test_implements_contract(self) -> None:
        with TemporaryDirectory() as directory:
            store = _store(Path(directory))
            self.assertIsInstance(store, ManagedAuthStore)
            store.migrate()

    def test_persists_auth_state(self) -> None:
        with TemporaryDirectory() as directory:
            store = _store(Path(directory))
            store.migrate()
            store.create_user("subject-1", "User@example.com", "correct horse battery staple")
            store.trust_device("subject-1", "device-1")
            store.block_phone("+61000000000")
            issued = datetime.now(timezone.utc).isoformat()
            expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            store.save_session("opaque-token", "subject-1", "device-1", issued, expires)

            user = store.find_user("user@EXAMPLE.com")
            session = store.get_session("opaque-token")

            self.assertIsNotNone(user)
            self.assertEqual(user["subject_id"], "subject-1")
            self.assertTrue(store.device_trusted("subject-1", "device-1"))
            self.assertTrue(store.phone_blocked("+61000000000"))
            self.assertIsNotNone(session)
            self.assertEqual(session["subject_id"], "subject-1")
            self.assertFalse(session["revoked"])

            store.revoke_session("opaque-token")
            self.assertTrue(store.get_session("opaque-token")["revoked"])

    def test_audit_chain_is_linked(self) -> None:
        with TemporaryDirectory() as directory:
            store = _store(Path(directory))
            store.migrate()
            first = store.add_audit_fingerprint("sign_in", "subject-1", "device-hash-1")
            second = store.add_audit_fingerprint("refresh", "subject-1", "device-hash-1")
            self.assertNotEqual(first, second)
            self.assertEqual(store.last_audit_hash(), second)

    def test_requires_pepper(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "pepper"):
            ManagedDbAuthStore(lambda: sqlite3.connect(":memory:"), pepper="", placeholder="?", audit_lock_clause="")


if __name__ == "__main__":
    unittest.main()
