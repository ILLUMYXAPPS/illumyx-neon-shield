"""Real PostgreSQL integration tests for serialized audit-chain writes.

These tests are skipped unless NEON_SHIELD_TEST_DATABASE_URL points at a
DISPOSABLE test database. They create and drop an isolated schema; never point
this variable at production or a database containing user data.
"""
from __future__ import annotations

import os
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

try:
    import psycopg
except ImportError:  # pragma: no cover - exercised only when optional dependency absent
    psycopg = None

from backend.migrations import MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS
from backend.serialized_audit_store import SerializedAuditManagedDbAuthStore

_DSN = os.environ.get("NEON_SHIELD_TEST_DATABASE_URL")
_SENTINEL = "0" * 64


@unittest.skipUnless(_DSN and psycopg is not None, "requires psycopg and a disposable PostgreSQL test database")
class PostgreSQLAuditChainIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = "neon_audit_test_" + uuid.uuid4().hex
        with psycopg.connect(_DSN, connect_timeout=10) as connection:
            connection.execute(f'CREATE SCHEMA "{cls.schema}"')

        def connect():
            # schema is generated locally from hex characters, not user input.
            return psycopg.connect(
                _DSN,
                connect_timeout=10,
                options=f"-c search_path={cls.schema}",
                application_name="neon-shield-audit-integration-test",
            )

        cls.connection_factory = staticmethod(connect)

    @classmethod
    def tearDownClass(cls) -> None:
        with psycopg.connect(_DSN, connect_timeout=10) as connection:
            connection.execute(f'DROP SCHEMA IF EXISTS "{cls.schema}" CASCADE')

    def setUp(self) -> None:
        self.runner = MigrationRunner(
            self.connection_factory, PRODUCTION_MIGRATIONS, placeholder="%s"
        )
        self.assertEqual(self.runner.apply_pending(), 4)
        self.assertEqual(self.runner.apply_pending(), 4)
        self.store = SerializedAuditManagedDbAuthStore(
            self.connection_factory, pepper="integration-test-pepper", placeholder="%s"
        )
        with self.connection_factory() as connection:
            connection.execute("DELETE FROM audit_events")
            connection.execute(
                "UPDATE audit_chain_head SET last_event_hash=%s WHERE chain_id=1",
                (_SENTINEL,),
            )

    def _events_and_head(self):
        with self.connection_factory() as connection:
            rows = connection.execute(
                "SELECT event_hash, previous_hash FROM audit_events"
            ).fetchall()
            head = connection.execute(
                "SELECT last_event_hash FROM audit_chain_head WHERE chain_id=1"
            ).fetchone()[0]
        return rows, head

    def _assert_single_complete_chain(self, expected_count: int) -> None:
        rows, head = self._events_and_head()
        self.assertEqual(len(rows), expected_count, "a committed audit event was lost or duplicated")
        by_hash = {event_hash: previous_hash for event_hash, previous_hash in rows}
        self.assertEqual(len(by_hash), expected_count, "event hashes must be unique")
        previous_hashes = [previous_hash for _, previous_hash in rows]
        self.assertEqual(len(set(previous_hashes)), expected_count, "multiple events share a predecessor")
        self.assertEqual(previous_hashes.count(_SENTINEL), 1, "chain must have exactly one root")

        reached = set()
        current = _SENTINEL
        while True:
            successors = [event_hash for event_hash, predecessor in by_hash.items() if predecessor == current]
            if not successors:
                break
            self.assertEqual(len(successors), 1, "audit chain fork detected")
            current = successors[0]
            self.assertNotIn(current, reached, "audit chain cycle detected")
            reached.add(current)

        self.assertEqual(reached, set(by_hash), "orphaned events or gaps detected")
        self.assertEqual(head, current, "durable audit-chain head does not match the final event")

    def test_concurrent_appends_from_independent_connections_form_one_chain(self) -> None:
        workers = 12
        events_per_worker = 8
        barrier = threading.Barrier(workers)

        def append_worker(worker_id: int) -> list[str]:
            barrier.wait(timeout=15)
            hashes = []
            for event_number in range(events_per_worker):
                hashes.append(
                    self.store.add_audit_fingerprint(
                        "integration_concurrent",
                        f"worker-{worker_id}-event-{event_number}",
                        f"device-{worker_id}",
                    )
                )
            return hashes

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(append_worker, range(workers)))

        all_hashes = [event_hash for worker_hashes in results for event_hash in worker_hashes]
        self.assertEqual(len(all_hashes), workers * events_per_worker)
        self.assertEqual(len(set(all_hashes)), len(all_hashes))
        self._assert_single_complete_chain(workers * events_per_worker)

    def test_failed_event_insert_rolls_back_without_advancing_head(self) -> None:
        with self.connection_factory() as connection:
            connection.execute(
                """
                CREATE FUNCTION reject_audit_event() RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION 'intentional integration-test insert failure';
                END;
                $$ LANGUAGE plpgsql
                """
            )
            connection.execute(
                """
                CREATE TRIGGER reject_audit_event_trigger
                BEFORE INSERT ON audit_events
                FOR EACH ROW EXECUTE FUNCTION reject_audit_event()
                """
            )

        before_rows, before_head = self._events_and_head()
        self.assertEqual(before_rows, [])
        self.assertEqual(before_head, _SENTINEL)

        with self.assertRaises(psycopg.Error):
            self.store.add_audit_fingerprint("must_rollback", "subject-test", "device-test")

        after_rows, after_head = self._events_and_head()
        self.assertEqual(after_rows, [])
        self.assertEqual(after_head, before_head)


if __name__ == "__main__":
    unittest.main()
