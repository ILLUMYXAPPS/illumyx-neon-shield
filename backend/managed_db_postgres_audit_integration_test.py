"""Real PostgreSQL integration tests for audit-chain locking and migrations.

The workflow provisions a disposable PostgreSQL service. Never point the test
DSN at production or a database containing user data.
"""
from __future__ import annotations

import os
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

try:
    import psycopg
except ImportError:  # pragma: no cover - optional integration dependency
    psycopg = None

from backend.migrations import MigrationRunner
from backend.managed_db_store import ManagedDbAuthStore
from backend.production_migrations import PRODUCTION_MIGRATIONS

_DSN = os.environ.get("NEON_SHIELD_TEST_DATABASE_URL")
_SENTINEL = "0" * 64


@unittest.skipUnless(_DSN and psycopg is not None, "requires a disposable PostgreSQL test database")
class AuditChainPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = "neon_audit_it_" + uuid.uuid4().hex
        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            connection.execute(f'CREATE SCHEMA "{cls.schema}"')

        def connect():
            return psycopg.connect(
                _DSN,
                connect_timeout=5,
                options=f"-c search_path={cls.schema}",
                application_name="neon-shield-audit-integration-test",
            )

        cls.connection_factory = staticmethod(connect)
        cls.runner = MigrationRunner(
            cls.connection_factory, PRODUCTION_MIGRATIONS, placeholder="%s"
        )
        cls.store = ManagedDbAuthStore(
            cls.connection_factory,
            pepper="integration-test-only-pepper",
            placeholder="%s",
            audit_lock_clause=" FOR UPDATE",
        )

    @classmethod
    def tearDownClass(cls):
        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            connection.execute(f'DROP SCHEMA IF EXISTS "{cls.schema}" CASCADE')

    def setUp(self):
        self.assertEqual(self.runner.apply_pending(), 4)
        with self.connection_factory() as connection:
            connection.execute("DROP TRIGGER IF EXISTS reject_audit_event_trigger ON audit_events")
            connection.execute("DROP FUNCTION IF EXISTS reject_audit_event_fn()")
            connection.execute("DELETE FROM audit_events")
            connection.execute(
                "UPDATE audit_chain_head SET event_hash=%s WHERE chain_id=1",
                (_SENTINEL,),
            )

    def test_concurrent_appends_form_one_unbroken_chain(self):
        workers = 12
        events_per_worker = 5
        barrier = threading.Barrier(workers)

        def append_worker(worker_id):
            barrier.wait(timeout=10)
            return [
                self.store.add_audit_fingerprint(
                    "integration_concurrent",
                    f"worker-{worker_id}-event-{number}",
                    f"device-{worker_id}",
                )
                for number in range(events_per_worker)
            ]

        with ThreadPoolExecutor(max_workers=workers) as pool:
            hashes = [event_hash for result in pool.map(append_worker, range(workers)) for event_hash in result]

        with self.connection_factory() as connection:
            rows = connection.execute(
                "SELECT event_hash, previous_hash FROM audit_events"
            ).fetchall()
            head = connection.execute(
                "SELECT event_hash FROM audit_chain_head WHERE chain_id=1"
            ).fetchone()[0]

        self.assertEqual(len(hashes), workers * events_per_worker)
        self.assertEqual(len(rows), len(hashes))
        by_hash = {event_hash: previous_hash for event_hash, previous_hash in rows}
        self.assertEqual(len(by_hash), len(rows))
        predecessors = [previous_hash for _, previous_hash in rows]
        self.assertEqual(predecessors.count(_SENTINEL), 1)
        self.assertEqual(len(set(predecessors)), len(predecessors))
        reached = set()
        current = _SENTINEL
        while True:
            successors = [event_hash for event_hash, previous_hash in by_hash.items() if previous_hash == current]
            if not successors:
                break
            self.assertEqual(len(successors), 1, "audit chain fork detected")
            current = successors[0]
            self.assertNotIn(current, reached, "audit chain cycle detected")
            reached.add(current)
        self.assertEqual(reached, set(by_hash), "orphaned audit event detected")
        self.assertEqual(head, current)

    def test_failed_event_insert_rolls_back_head_update(self):
        with self.connection_factory() as connection:
            connection.execute(
                """
                CREATE FUNCTION reject_audit_event_fn() RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION 'intentional audit integration-test failure';
                END;
                $$ LANGUAGE plpgsql
                """
            )
            connection.execute(
                """
                CREATE TRIGGER reject_audit_event_trigger
                BEFORE INSERT ON audit_events
                FOR EACH ROW EXECUTE FUNCTION reject_audit_event_fn()
                """
            )

        with self.assertRaises(psycopg.Error):
            self.store.add_audit_fingerprint("must_rollback", "subject-test", "device-test")

        with self.connection_factory() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0], 0)
            head = connection.execute(
                "SELECT event_hash FROM audit_chain_head WHERE chain_id=1"
            ).fetchone()[0]
        self.assertEqual(head, _SENTINEL)

    def test_versioned_migration_backfills_existing_chain_head(self):
        schema = "neon_audit_mig_" + uuid.uuid4().hex
        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            connection.execute(f'CREATE SCHEMA "{schema}"')

        def connect_legacy():
            return psycopg.connect(
                _DSN, connect_timeout=5, options=f"-c search_path={schema}"
            )

        try:
            legacy_runner = MigrationRunner(
                connect_legacy, PRODUCTION_MIGRATIONS[:3], placeholder="%s"
            )
            self.assertEqual(legacy_runner.apply_pending(), 3)
            with connect_legacy() as connection:
                connection.execute(
                    "INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) VALUES(%s,%s,%s,%s,%s,%s)",
                    ("a" * 64, "first", "2026-10-16T10:02:00+00:00", None, "device-1", _SENTINEL),
                )
                connection.execute(
                    "INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) VALUES(%s,%s,%s,%s,%s,%s)",
                    ("b" * 64, "second", "2026-10-16T10:01:00+00:00", None, "device-2", "a" * 64),
                )
            full_runner = MigrationRunner(
                connect_legacy, PRODUCTION_MIGRATIONS, placeholder="%s"
            )
            self.assertEqual(full_runner.apply_pending(), 4)
            with connect_legacy() as connection:
                head = connection.execute(
                    "SELECT event_hash FROM audit_chain_head WHERE chain_id=1"
                ).fetchone()[0]
            self.assertEqual(head, "b" * 64)
        finally:
            with psycopg.connect(_DSN, connect_timeout=5) as connection:
                connection.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


    def test_versioned_migration_rejects_forked_legacy_chain(self):
        schema = "neon_audit_fork_" + uuid.uuid4().hex
        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            connection.execute(f'CREATE SCHEMA "{schema}"')

        def connect_legacy():
            return psycopg.connect(
                _DSN, connect_timeout=5, options=f"-c search_path={schema}"
            )

        try:
            legacy_runner = MigrationRunner(
                connect_legacy, PRODUCTION_MIGRATIONS[:3], placeholder="%s"
            )
            self.assertEqual(legacy_runner.apply_pending(), 3)
            with connect_legacy() as connection:
                connection.execute(
                    "INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) VALUES(%s,%s,%s,%s,%s,%s)",
                    ("a" * 64, "first", "2026-10-16T10:00:00+00:00", None, "device-1", _SENTINEL),
                )
                connection.execute(
                    "INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) VALUES(%s,%s,%s,%s,%s,%s)",
                    ("b" * 64, "fork", "2026-10-16T10:01:00+00:00", None, "device-2", _SENTINEL),
                )

            full_runner = MigrationRunner(
                connect_legacy, PRODUCTION_MIGRATIONS, placeholder="%s"
            )
            with self.assertRaises(psycopg.Error):
                full_runner.apply_pending()
            with connect_legacy() as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM neon_schema_migrations WHERE version=4"
                    ).fetchone()[0],
                    0,
                )
                # PostgreSQL rolls back the failed migration transaction, including
                # CREATE TABLE. Verify the table is absent rather than querying it.
                self.assertIsNone(
                    connection.execute(
                        "SELECT to_regclass('audit_chain_head')"
                    ).fetchone()[0]
                )
        finally:
            with psycopg.connect(_DSN, connect_timeout=5) as connection:
                connection.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


if __name__ == "__main__":
    unittest.main()
