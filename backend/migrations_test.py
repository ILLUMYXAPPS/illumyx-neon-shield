"""Regression tests for the production migration boundary."""
from __future__ import annotations

import sqlite3
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.migrations import Migration, MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS


class MigrationRunnerTests(unittest.TestCase):
    def test_production_migrations_are_contiguous_and_create_pairing_and_family_state(self) -> None:
        self.assertEqual([migration.version for migration in PRODUCTION_MIGRATIONS], [1, 2, 3, 4, 5, 6, 7, 8, 9])
        with TemporaryDirectory() as directory:
            path = Path(directory) / "production-migrations.sqlite3"
            runner = MigrationRunner(lambda: sqlite3.connect(path), PRODUCTION_MIGRATIONS)
            self.assertEqual(runner.apply_pending(), 9)
            self.assertEqual(runner.apply_pending(), 9)
            connection = sqlite3.connect(path)
            try:
                table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='sign_in_rate_limits'"
                ).fetchone()
                versions = connection.execute(
                    "SELECT version, name FROM neon_schema_migrations ORDER BY version"
                ).fetchall()
                subscription_table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='verified_subscriptions'"
                ).fetchone()
                notification_table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='store_notification_events'"
                ).fetchone()
                family_table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='family_memberships'"
                ).fetchone()
                binding_table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='store_account_bindings'"
                ).fetchone()
                pairing_table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='device_pairing_requests'"
                ).fetchone()
                labels_table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='device_labels'"
                ).fetchone()
                invitation_table = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='family_invitations'"
                ).fetchone()
                audit_head = connection.execute(
                    "SELECT event_hash FROM audit_chain_head WHERE chain_id=1"
                ).fetchone()
            finally:
                connection.close()
            self.assertIsNotNone(table)
            self.assertEqual(versions, [
                (1, "create_auth_tables"),
                (2, "create_auth_indexes"),
                (3, "create_sign_in_rate_limits"),
                (4, "create_store_subscription_records"),
                (5, "create_store_account_bindings"),
                (6, "create_family_membership_records"),
                (7, "create_device_pairing_tables"),
                (8, "create_family_invitations"),
                (9, "create_serialized_audit_chain_head"),
            ])
            self.assertIsNotNone(subscription_table)
            self.assertIsNotNone(notification_table)
            self.assertIsNotNone(binding_table)
            self.assertIsNotNone(family_table)
            self.assertIsNotNone(pairing_table)
            self.assertIsNotNone(labels_table)
            self.assertIsNotNone(invitation_table)
            self.assertEqual(audit_head, ("0000000000000000000000000000000000000000000000000000000000000000",))

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


    def test_concurrent_runners_serialize_and_apply_each_migration_once(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "concurrent-migrations.sqlite3"
            migrations = (
                Migration(1, "create_users", ("CREATE TABLE users (id INTEGER PRIMARY KEY)",)),
                Migration(2, "add_name", ("ALTER TABLE users ADD COLUMN name TEXT",)),
            )
            barrier = threading.Barrier(2)
            outcomes = []
            failures = []

            def apply():
                try:
                    barrier.wait(timeout=5)
                    runner = MigrationRunner(
                        lambda: sqlite3.connect(path, timeout=15), migrations
                    )
                    outcomes.append(runner.apply_pending())
                except Exception as exc:
                    failures.append(exc)

            threads = [threading.Thread(target=apply) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)

            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(failures, [])
            self.assertEqual(outcomes, [2, 2])
            connection = sqlite3.connect(path)
            try:
                self.assertEqual(
                    connection.execute(
                        "SELECT version,name FROM neon_schema_migrations ORDER BY version"
                    ).fetchall(),
                    [(1, "create_users"), (2, "add_name")],
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM neon_schema_migration_lock WHERE lock_id=1"
                    ).fetchone()[0],
                    1,
                )
            finally:
                connection.close()

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
