"""Regression tests for the production migration boundary."""
from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.migrations import Migration, MigrationRunner


class MigrationRunnerTests(unittest.TestCase):
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
