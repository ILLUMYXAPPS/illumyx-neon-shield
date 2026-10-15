"""Focused regression tests for the DB-API managed auth adapter."""
from __future__ import annotations

import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
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

    def test_distributed_rate_limit_state_is_persistent_and_bounded(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "managed-test.sqlite3"
            first = ManagedDbAuthStore(lambda: sqlite3.connect(path), pepper="test-pepper", placeholder="?", audit_lock_clause="")
            first.migrate()
            now = datetime.now(timezone.utc).isoformat()
            self.assertFalse(first.sign_in_rate_limited("user@example.com", now, 300, 5))
            for _ in range(5):
                first.record_sign_in_failure("user@example.com", now, 300, 5)
            first.close()

            second = ManagedDbAuthStore(lambda: sqlite3.connect(path), pepper="test-pepper", placeholder="?", audit_lock_clause="")
            self.assertTrue(second.sign_in_rate_limited("user@example.com", now, 300, 5))
            second.clear_sign_in_failures("user@example.com")
            self.assertFalse(second.sign_in_rate_limited("user@example.com", now, 300, 5))
            second.close()

    def test_rate_limit_window_expiry_resets_counter(self) -> None:
        with TemporaryDirectory() as directory:
            store = _store(Path(directory))
            store.migrate()
            old = (datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat()
            for _ in range(5):
                store.record_sign_in_failure("user@example.com", old, 300, 5)
            now = datetime.now(timezone.utc).isoformat()
            self.assertFalse(store.sign_in_rate_limited("user@example.com", now, 300, 5))
            store.close()

    def test_audit_chain_is_linked(self) -> None:
        with TemporaryDirectory() as directory:
            store = _store(Path(directory))
            store.migrate()
            first = store.add_audit_fingerprint("sign_in", "subject-1", "device-hash-1")
            second = store.add_audit_fingerprint("refresh", "subject-1", "device-hash-1")
            rows = sqlite3.connect(store._connection_factory.__closure__[0].cell_contents if False else str(Path(directory) / "managed-test.sqlite3"))
            try:
                events = rows.execute("SELECT event_hash, previous_hash FROM audit_events").fetchall()
            finally:
                rows.close()
            self.assertNotEqual(first, second)
            self.assertEqual(store.last_audit_hash(), second)
            self.assertEqual(events[0][1], "0" * 64)
            self.assertEqual(events[1][1], events[0][0])

    def test_concurrent_audit_writes_form_one_unbroken_chain(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "managed-test.sqlite3"
            store = ManagedDbAuthStore(lambda: sqlite3.connect(path, timeout=15), pepper="test-pepper", placeholder="?", audit_lock_clause="")
            store.migrate()

            def append(index: int) -> str:
                return store.add_audit_fingerprint(f"event-{index}", "subject-1", f"device-{index}")

            with ThreadPoolExecutor(max_workers=12) as pool:
                hashes = list(pool.map(append, range(24)))

            db = sqlite3.connect(path)
            try:
                rows = db.execute("SELECT event_hash, previous_hash FROM audit_events").fetchall()
            finally:
                db.close()
            self.assertEqual(len(hashes), 24)
            self.assertEqual(len(rows), 24)
            by_hash = {event_hash: previous_hash for event_hash, previous_hash in rows}
            self.assertEqual(len(by_hash), 24)
            roots = [event_hash for event_hash, previous_hash in rows if previous_hash == "0" * 64]
            self.assertEqual(len(roots), 1)
            for event_hash, previous_hash in rows:
                if previous_hash != "0" * 64:
                    self.assertIn(previous_hash, by_hash)
            self.assertEqual(store.last_audit_hash(), next(event_hash for event_hash, _ in rows if event_hash == store.last_audit_hash()))
            self.assertEqual(sum(1 for _, previous_hash in rows if previous_hash == store.last_audit_hash()), 0)

    def test_requires_pepper(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "pepper"):
            ManagedDbAuthStore(lambda: sqlite3.connect(":memory:"), pepper="", placeholder="?", audit_lock_clause="")


if __name__ == "__main__":
    unittest.main()
