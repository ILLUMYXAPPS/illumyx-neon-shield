"""Regression tests for managed DB safety boundaries."""
from __future__ import annotations

import sqlite3
import unittest
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


if __name__ == "__main__":
    unittest.main()
