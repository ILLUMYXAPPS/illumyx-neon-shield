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
            self.assertNotEqual(first, second)
            self.assertEqual(store.last_audit_hash(), second)

    def test_rate_limit_concurrent_insert_winner_is_reread_and_incremented(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        state = {"selects": 0, "updates": [], "commits": 0, "closed": 0}

        class ConflictCursor:
            rowcount = -1
            current_row = None

            def execute(self, query, params=()):
                if query.startswith("SELECT failure_count"):
                    state["selects"] += 1
                    self.current_row = None if state["selects"] == 1 else (1, now)
                elif query.startswith("INSERT INTO sign_in_rate_limits"):
                    self.rowcount = 0
                elif query.startswith("UPDATE sign_in_rate_limits SET failure_count=?"):
                    state["updates"].append(params)
                    self.rowcount = 1
                else:
                    raise AssertionError(f"Unexpected SQL in test: {query}")
                return self

            def fetchone(self):
                row = self.current_row
                self.current_row = None
                return row

            def close(self):
                return None

        class ConflictConnection:
            def cursor(self):
                return ConflictCursor()

            def commit(self):
                state["commits"] += 1

            def rollback(self):
                raise AssertionError("successful conflict recovery must not roll back")

            def close(self):
                state["closed"] += 1

        store = ManagedDbAuthStore(lambda: ConflictConnection(), pepper="test-pepper", placeholder="?", audit_lock_clause="")
        allowed = store.reserve_sign_in_attempt("user@example.com", now, 300, 5)

        self.assertTrue(allowed)
        self.assertEqual(state["selects"], 2)
        self.assertEqual(state["updates"][0][0], 2)
        self.assertEqual(state["commits"], 1)
        self.assertEqual(state["closed"], 1)

    def test_rate_limit_insert_failure_is_not_recursively_retried(self) -> None:
        attempts = {"connections": 0, "closed": 0, "rollbacks": 0}

        class FailingCursor:
            rowcount = -1

            def execute(self, query, params=()):
                if query.startswith("SELECT failure_count"):
                    return self
                if query.startswith("INSERT INTO sign_in_rate_limits"):
                    raise sqlite3.OperationalError("simulated database outage")
                raise AssertionError(f"Unexpected SQL in test: {query}")

            def fetchone(self):
                return None

            def close(self):
                return None

        class FailingConnection:
            def cursor(self):
                return FailingCursor()

            def rollback(self):
                attempts["rollbacks"] += 1

            def commit(self):
                raise AssertionError("failed reservation must not commit")

            def close(self):
                attempts["closed"] += 1

        def connect():
            attempts["connections"] += 1
            return FailingConnection()

        store = ManagedDbAuthStore(connect, pepper="test-pepper", placeholder="?", audit_lock_clause="")
        now = datetime.now(timezone.utc).isoformat()
        with self.assertRaisesRegex(sqlite3.OperationalError, "simulated database outage"):
            store.reserve_sign_in_attempt("user@example.com", now, 300, 5)

        self.assertEqual(attempts["connections"], 1)
        self.assertEqual(attempts["rollbacks"], 1)
        self.assertEqual(attempts["closed"], 1)

    def test_requires_pepper(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "pepper"):
            ManagedDbAuthStore(lambda: sqlite3.connect(":memory:"), pepper="", placeholder="?", audit_lock_clause="")


if __name__ == "__main__":
    unittest.main()
