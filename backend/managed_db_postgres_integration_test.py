"""PostgreSQL integration tests for managed sign-in rate-limit concurrency.

Only run against a disposable test database. CI provisions a fresh PostgreSQL
service for this workflow; never point the DSN at production or user data.
"""
from __future__ import annotations

import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

try:
    import psycopg
except ImportError:  # pragma: no cover - optional integration dependency
    psycopg = None

from backend.managed_db_store import ManagedDbAuthStore

_DSN = os.environ.get("NEON_SHIELD_TEST_DATABASE_URL")


@unittest.skipUnless(_DSN and psycopg is not None, "requires a disposable PostgreSQL test database")
class ManagedRateLimitPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = ManagedDbAuthStore(
            lambda: psycopg.connect(_DSN, connect_timeout=5),
            pepper="integration-test-only-pepper",
            placeholder="%s",
            audit_lock_clause=" FOR UPDATE",
        )
        cls.store.migrate()

    def setUp(self):
        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            connection.execute("DROP TRIGGER IF EXISTS fail_rate_limit_insert ON sign_in_rate_limits")
            connection.execute("DROP FUNCTION IF EXISTS fail_rate_limit_insert_fn()")
            connection.execute("DELETE FROM sign_in_rate_limits")

    def test_concurrent_first_use_reservations_obey_limit(self):
        workers = 12
        limit = 3
        barrier = threading.Barrier(workers)
        now = "2026-10-16T00:00:00+00:00"

        def reserve(_):
            barrier.wait(timeout=10)
            return self.store.reserve_sign_in_attempt(
                "first-use@example.invalid", now, 300, limit
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(reserve, range(workers)))

        self.assertEqual(sum(results), limit)
        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            row = connection.execute(
                "SELECT failure_count FROM sign_in_rate_limits"
            ).fetchone()
        self.assertEqual(row[0], limit + 1)

    def test_concurrent_failure_records_are_not_lost(self):
        workers = 12
        barrier = threading.Barrier(workers)
        now = "2026-10-16T00:00:00+00:00"

        def record(_):
            barrier.wait(timeout=10)
            self.store.record_sign_in_failure(
                "failure-record@example.invalid", now, 300, 3
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(record, range(workers)))

        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            row = connection.execute(
                "SELECT failure_count FROM sign_in_rate_limits WHERE identity_hash = %s",
                # The identity is hashed by the adapter, so query the single row.
                ("not-the-real-hash",),
            ).fetchone()
            total_rows = connection.execute(
                "SELECT COUNT(*) FROM sign_in_rate_limits"
            ).fetchone()[0]
            failure_count = connection.execute(
                "SELECT MAX(failure_count) FROM sign_in_rate_limits"
            ).fetchone()[0]
        self.assertIsNone(row)
        self.assertEqual(total_rows, 1)
        self.assertEqual(failure_count, 3)

    def test_persistent_database_error_fails_closed_without_retry(self):
        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            connection.execute(
                """
                CREATE FUNCTION fail_rate_limit_insert_fn() RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION 'intentional rate-limit integration-test failure';
                END;
                $$ LANGUAGE plpgsql
                """
            )
            connection.execute(
                """
                CREATE TRIGGER fail_rate_limit_insert
                BEFORE INSERT ON sign_in_rate_limits
                FOR EACH ROW EXECUTE FUNCTION fail_rate_limit_insert_fn()
                """
            )

        with self.assertRaises(psycopg.Error):
            self.store.reserve_sign_in_attempt(
                "database-error@example.invalid",
                "2026-10-16T00:00:00+00:00",
                300,
                3,
            )

        with psycopg.connect(_DSN, connect_timeout=5) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM sign_in_rate_limits").fetchone()[0],
                0,
            )


if __name__ == "__main__":
    unittest.main()
