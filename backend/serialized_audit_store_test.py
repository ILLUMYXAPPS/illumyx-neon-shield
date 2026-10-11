"""Regression tests for serialized audit-chain writes."""
from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.migrations import MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS
from backend.serialized_audit_store import SerializedAuditManagedDbAuthStore


class SerializedAuditStoreTests(unittest.TestCase):
    def test_each_append_advances_durable_head_and_links_to_previous_event(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "audit.sqlite3"
            connect = lambda: sqlite3.connect(path, timeout=5)
            runner = MigrationRunner(connect, PRODUCTION_MIGRATIONS)
            self.assertEqual(runner.apply_pending(), 4)
            store = SerializedAuditManagedDbAuthStore(
                connect, pepper="test-pepper", placeholder="?", audit_lock_clause=""
            )

            first = store.add_audit_fingerprint("sign_in", "subject-1", "device-hash-1")
            second = store.add_audit_fingerprint("refresh", "subject-1", "device-hash-1")

            self.assertNotEqual(first, second)
            self.assertEqual(store.last_audit_hash(), second)
            connection = connect()
            try:
                first_row = connection.execute(
                    "SELECT previous_hash FROM audit_events WHERE event_hash=?", (first,)
                ).fetchone()
                second_row = connection.execute(
                    "SELECT previous_hash FROM audit_events WHERE event_hash=?", (second,)
                ).fetchone()
                head = connection.execute(
                    "SELECT last_event_hash FROM audit_chain_head WHERE chain_id=1"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(first_row, ("0" * 64,))
            self.assertEqual(second_row, (first,))
            self.assertEqual(head, (second,))

    def test_fails_closed_if_migration_has_not_created_head(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "unmigrated.sqlite3"
            store = SerializedAuditManagedDbAuthStore(
                lambda: sqlite3.connect(path), pepper="test-pepper",
                placeholder="?", audit_lock_clause=""
            )
            with self.assertRaisesRegex(RuntimeError, "audit chain head is missing"):
                store.add_audit_fingerprint("sign_in", "subject-1", "device-hash-1")


if __name__ == "__main__":
    unittest.main()
