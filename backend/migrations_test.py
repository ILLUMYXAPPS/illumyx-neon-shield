"""Regression tests for the production migration boundary."""
from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.migrations import Migration, MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS


class MigrationRunnerTests(unittest.TestCase):
    def test_production_migrations_are_contiguous_and_create_audit_head(self) -> None:
        self.assertEqual([migration.version for migration in PRODUCTION_MIGRATIONS], [1, 2, 3, 4])
        with TemporaryDirectory() as directory:
            path = Path(directory) / "production-migrations.sqlite3"
            runner = MigrationRunner(lambda: sqlite3.connect(path), PRODUCTION_MIGRATIONS)
            self.assertEqual(runner.apply_pending(), 4)
            self.assertEqual(runner.apply_pending(), 4)
            connection = sqlite3.connect(path)
            try:
                table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_chain_head'"
                ).fetchone()
                head = connection.execute(
                    "SELECT chain_id, last_event_hash FROM audit_chain_head"
                ).fetchall()
                versions = connection.execute("SELECT version, name FROM neon_schema_migrations ORDER BY version").fetchall()
            finally:
                connection.close()
            self.assertIsNotNone(table)
            self.assertEqual(head, [(1, "0" * 64)])
            self.assertEqual(versions, [
                (1, "create_auth_tables"),
                (2, "create_auth_indexes"),
                (3, "create_sign_in_rate_limits"),
                (4, "create_serialized_audit_chain_head"),
            ])

    def test_migration_backfills_existing_audit_chain_head(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "existing-audit.sqlite3"
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "CREATE TABLE audit_events (event_hash TEXT PRIMARY KEY, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, subject_id TEXT, device_fingerprint TEXT NOT NULL, previous_hash TEXT NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)",
                    ("older-event", "test", "2026-01-02T00:00:00+00:00", None, "device", "0" * 64),
                )
                connection.execute(
                    "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)",
                    ("actual-tip", "test", "2026-01-01T00:00:00+00:00", None, "device", "older-event"),
                )
                connection.commit()
            finally:
                connection.close()
            runner = MigrationRunner(lambda: sqlite3.connect(path), PRODUCTION_MIGRATIONS)
            self.assertEqual(runner.apply_pending(), 4)
            connection = sqlite3.connect(path)
            try:
                head = connection.execute(
                    "SELECT last_event_hash FROM audit_chain_head WHERE chain_id=1"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(head, ("actual-tip",))

    def test_ambiguous_audit_tip_is_not_backfilled(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ambiguous.sqlite3"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE audit_events (event_hash TEXT PRIMARY KEY, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, subject_id TEXT, device_fingerprint TEXT NOT NULL, previous_hash TEXT NOT NULL)")
            connection.executemany("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)", [("a", "test", "2026-01-01", None, "device", "0" * 64), ("b", "test", "2026-01-02", None, "device", "0" * 64)])
            connection.commit()
            connection.close()
            MigrationRunner(lambda: sqlite3.connect(path), PRODUCTION_MIGRATIONS).apply_pending()
            connection = sqlite3.connect(path)
            head = connection.execute("SELECT last_event_hash FROM audit_chain_head WHERE chain_id=1").fetchone()
            connection.close()
            self.assertIsNone(head)

    def test_applies_contiguous_migrations_and_is_idempotent(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "migrations.sqlite3"
            migrations = (
                Migration(1, "create_users", ("CREATE TABLE users (id INTEGER PRIMARY KEY)",)),
                Migration(2, "add_name", ("ALTER TABLE users ADD COLUMN name TEXT",)),
            )
            runner = MigrationRunner(lambda: sqlite3.connect(path), migrations)
            self.assertEqual(runner.current_version(), 0)
            self.assertEqual(runner.apply_pending(), 2)
            self.assertEqual(runner.apply_pending(), 2)

            connection = sqlite3.connect(path)
            try:
                versions = connection.execute(
                    "SELECT version, name FROM neon_schema_migrations ORDER BY version"
                ).fetchall()
                columns = [row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()]
            finally:
                connection.close()
            self.assertEqual(versions, [(1, "create_users"), (2, "add_name")])
            self.assertIn("name", columns)

    def test_rejects_duplicate_and_skipped_versions(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            MigrationRunner(
                lambda: sqlite3.connect(":memory:"),
                (Migration(1, "one", ("SELECT 1",)), Migration(1, "duplicate", ("SELECT 1",))),
            )
        with self.assertRaisesRegex(ValueError, "contiguous"):
            MigrationRunner(
                lambda: sqlite3.connect(":memory:"),
                (Migration(1, "one", ("SELECT 1",)), Migration(3, "three", ("SELECT 1",))),
            )

    def test_fails_closed_on_unknown_database_version(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "migrations.sqlite3"
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "CREATE TABLE neon_schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO neon_schema_migrations VALUES (9, 'future', '2026-01-01T00:00:00+00:00')"
                )
                connection.commit()
            finally:
                connection.close()

            runner = MigrationRunner(
                lambda: sqlite3.connect(path),
                (Migration(1, "one", ("CREATE TABLE users (id INTEGER PRIMARY KEY)",)),),
            )
            with self.assertRaisesRegex(RuntimeError, "unknown migration version"):
                runner.apply_pending()

    def test_rolls_back_failed_migration(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "migrations.sqlite3"
            migrations = (
                Migration(1, "create_users", ("CREATE TABLE users (id INTEGER PRIMARY KEY)",)),
                Migration(2, "broken", ("ALTER TABLE users ADD COLUMN name TEXT", "THIS IS NOT SQL")),
            )
            runner = MigrationRunner(lambda: sqlite3.connect(path), migrations)
            with self.assertRaises(sqlite3.OperationalError):
                runner.apply_pending()

            connection = sqlite3.connect(path)
            try:
                self.assertEqual(
                    connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone(),
                    None,
                )
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='neon_schema_migrations'").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM neon_schema_migrations").fetchone()[0], 0)
            finally:
                connection.close()

    def test_rejects_unsupported_placeholder(self) -> None:
        with self.assertRaisesRegex(ValueError, "placeholder"):
            MigrationRunner(lambda: sqlite3.connect(":memory:"), (), placeholder="bad")


if __name__ == "__main__":
    unittest.main()
