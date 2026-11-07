"""Real PostgreSQL integration tests for managed auth persistence.

These tests require NEON_TEST_DATABASE_URL and use isolated temporary schemas.
They never connect to or modify a production database.
"""
from __future__ import annotations

import os
import secrets
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import psycopg  # pylint: disable=import-error

from backend.managed_db_store import ManagedDbAuthStore


class ManagedPostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        dsn = os.environ.get("NEON_TEST_DATABASE_URL")
        if not dsn:
            raise unittest.SkipTest("NEON_TEST_DATABASE_URL is required")
        cls.dsn = dsn

    def setUp(self) -> None:
        self.schema = "neon_it_" + secrets.token_hex(8)
        with psycopg.connect(self.dsn) as connection:
            connection.execute(f'CREATE SCHEMA "{self.schema}"')

        def connect():
            return psycopg.connect(self.dsn, options=f"-c search_path={self.schema}")

        self.connect = connect
        self.store = ManagedDbAuthStore(connect, pepper="postgres-integration-test-pepper")
        self.store.migrate()

    def tearDown(self) -> None:
        with psycopg.connect(self.dsn) as connection:
            connection.execute(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE')

    def test_concurrent_audit_writes_form_one_unbroken_chain(self) -> None:
        event_count = 12
        with ThreadPoolExecutor(max_workers=6) as pool:
            hashes = list(pool.map(
                lambda index: self.store.add_audit_fingerprint(
                    "postgres_concurrency_test", "integration-subject", f"device-hash-{index}"
                ),
                range(event_count),
            ))

        self.assertEqual(len(set(hashes)), event_count)
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT event_hash, previous_hash FROM audit_events"
            ).fetchall()
        self.assertEqual(len(rows), event_count)

        by_previous = {}
        by_hash = {}
        for event_hash, previous_hash in rows:
            self.assertNotIn(previous_hash, by_previous, "audit chain must not fork")
            by_previous[previous_hash] = event_hash
            by_hash[event_hash] = previous_hash

        head = self.store.last_audit_hash()
        visited = set()
        while head != "0" * 64:
            self.assertIn(head, by_hash, "audit head must reference a persisted event")
            self.assertNotIn(head, visited, "audit chain must not contain a cycle")
            visited.add(head)
            head = by_hash[head]
        self.assertEqual(len(visited), event_count)

    def test_concurrent_session_rotation_has_exactly_one_winner(self) -> None:
        now = datetime.now(timezone.utc)
        self.store.create_user("rotation-subject", "rotation@example.test", "integration-password")
        self.store.save_session_hash(
            "old-session-token",
            "rotation-subject",
            "trusted-device-hash",
            now.isoformat(),
            (now + timedelta(hours=1)).isoformat(),
        )

        def rotate(index: int):
            return self.store.rotate_session(
                "old-session-token",
                f"replacement-session-{index}",
                now.isoformat(),
                (now + timedelta(hours=1)).isoformat(),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(rotate, range(2)))

        self.assertEqual(sum(result is not None for result in results), 1)
        with self.connect() as connection:
            active = connection.execute(
                "SELECT COUNT(*) FROM sessions WHERE revoked=0"
            ).fetchone()[0]
        self.assertEqual(active, 1)

    def test_concurrent_sign_in_reservations_enforce_exact_limit(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        limit = 5
        with ThreadPoolExecutor(max_workers=10) as pool:
            allowed = list(pool.map(
                lambda _: self.store.reserve_sign_in_attempt(
                    "parallel@example.test", now, 300, limit
                ),
                range(12),
            ))

        self.assertEqual(sum(allowed), limit)
        with self.connect() as connection:
            count = connection.execute(
                "SELECT failure_count FROM sign_in_rate_limits"
            ).fetchone()[0]
        self.assertEqual(count, limit + 1)


if __name__ == "__main__":
    unittest.main()
