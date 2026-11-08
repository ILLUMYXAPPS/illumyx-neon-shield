"""Regression tests for managed DB safety boundaries."""
from __future__ import annotations

import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.managed_db_store import ManagedDbAuthStore


class ManagedDbHardeningTests(unittest.TestCase):
    def test_rejects_unapproved_audit_lock_clause(self) -> None:
        with self.assertRaisesRegex(ValueError, "audit lock clause"):
            ManagedDbAuthStore(lambda: sqlite3.connect(":memory:"), pepper="test-pepper", placeholder="?", audit_lock_clause="; DROP TABLE users")

    def test_accepts_postgresql_row_lock_clause(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "managed.sqlite3"
            store = ManagedDbAuthStore(lambda: sqlite3.connect(path), pepper="test-pepper", placeholder="?", audit_lock_clause=" FOR UPDATE")
            store.migrate()
            self.assertEqual(store.last_audit_hash(), "0" * 64)

    def test_connection_failure_rolls_back_and_closes(self) -> None:
        class FailingConnection:
            def __init__(self) -> None:
                self.rolled_back = False
                self.closed = False

            def cursor(self):
                raise RuntimeError("database failure")

            def rollback(self):
                self.rolled_back = True

            def close(self):
                self.closed = True

        connection = FailingConnection()
        store = ManagedDbAuthStore(lambda: connection, pepper="test-pepper", placeholder="?")
        with self.assertRaisesRegex(RuntimeError, "database failure"):
            store.find_user("user@example.com")
        self.assertTrue(connection.closed)
        self.assertTrue(connection.rolled_back)


    def test_sign_in_reservation_database_error_fails_closed_without_retry_recursion(self) -> None:
        class FailingCursor:
            def execute(self, query, parameters=()):
                if query.startswith("SELECT failure_count"):
                    return None
                if query.startswith("INSERT INTO sign_in_rate_limits"):
                    raise RuntimeError("database unavailable")
                raise AssertionError(f"unexpected query: {query}")

            def fetchone(self):
                return None

            def close(self):
                pass

        class FailingConnection:
            def __init__(self) -> None:
                self.rolled_back = False
                self.closed = False

            def cursor(self):
                return FailingCursor()

            def rollback(self):
                self.rolled_back = True

            def close(self):
                self.closed = True

        connection = FailingConnection()
        factory_calls = 0

        def connection_factory():
            nonlocal factory_calls
            factory_calls += 1
            return connection

        store = ManagedDbAuthStore(connection_factory, pepper="test-pepper", placeholder="?", audit_lock_clause="")
        now = "2026-10-15T00:00:00+00:00"
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            store.reserve_sign_in_attempt("user@example.com", now, 300, 5)

        self.assertEqual(factory_calls, 1)
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.closed)


    def test_concurrent_first_sign_in_reservations_are_serialized(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "rate-limit.sqlite3"

            def make_store() -> ManagedDbAuthStore:
                return ManagedDbAuthStore(
                    lambda: sqlite3.connect(path, timeout=15),
                    pepper="test-pepper",
                    placeholder="?",
                    audit_lock_clause="",
                )

            make_store().migrate()
            now = "2026-10-15T00:00:00+00:00"

            def reserve(_: int) -> bool:
                return make_store().reserve_sign_in_attempt(
                    "user@example.com", now, 300, 3
                )

            with ThreadPoolExecutor(max_workers=8) as executor:
                outcomes = list(executor.map(reserve, range(12)))

            self.assertEqual(sum(outcomes), 3)
            with sqlite3.connect(path) as connection:
                row = connection.execute(
                    "SELECT failure_count FROM sign_in_rate_limits"
                ).fetchone()
            self.assertEqual(row[0], 4)

    def test_concurrent_first_sign_in_failures_are_not_lost(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "failure-limit.sqlite3"

            def make_store() -> ManagedDbAuthStore:
                return ManagedDbAuthStore(
                    lambda: sqlite3.connect(path, timeout=15),
                    pepper="test-pepper",
                    placeholder="?",
                    audit_lock_clause="",
                )

            make_store().migrate()
            now = "2026-10-15T00:00:00+00:00"

            def record(_: int) -> None:
                make_store().record_sign_in_failure(
                    "user@example.com", now, 300, 3
                )

            with ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(record, range(12)))

            with sqlite3.connect(path) as connection:
                row = connection.execute(
                    "SELECT failure_count FROM sign_in_rate_limits"
                ).fetchone()
            self.assertEqual(row[0], 3)


if __name__ == "__main__":
    unittest.main()
