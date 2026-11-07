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
from backend.device_allowance import FamilyMembershipRepository, StoreDeviceAllowanceResolver
from backend.device_limits import DeviceLimitExceeded
from backend.family_invitations import FamilyInvitationService
from backend.migrations import MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS
from backend.service import PersistentIdentityService
from backend.subscription_store import StoreSubscriptionRepository
from auth_server_contract import SignInRequest


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
        MigrationRunner(
            connect, PRODUCTION_MIGRATIONS, placeholder="%s"
        ).apply_pending()

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

    def _create_family_subscription(self) -> StoreSubscriptionRepository:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO verified_subscriptions "
                "(subscription_id,subject_id,provider,application_id,product_id,package,environment,"
                "account_binding_id,transaction_id,original_transaction_id,purchase_token_hash,"
                "expires_at,revoked,verified_at,updated_at) "
                "VALUES (%s,%s,'apple','com.illumyx.illumyxapp','family_monthly','premium_family',"
                "'production','family-binding','family-txn','family-original','family-token-hash',"
                "NULL,0,%s,%s)",
                ("family-original", "family-owner", now, now),
            )
        return StoreSubscriptionRepository(
            self.connect, pepper="postgres-integration-subscription-pepper", placeholder="%s"
        )

    def test_postgres_family_invitation_acceptance_persists_membership(self) -> None:
        self.store.create_user("family-owner", "family-owner@example.test", "owner-password")
        self.store.create_user("family-member", "family-member@example.test", "member-password")
        subscriptions = self._create_family_subscription()
        invitations = FamilyInvitationService(
            self.connect, subscriptions, placeholder="%s"
        )

        created = invitations.create_invitation("family-owner")
        invitations.accept_invitation("family-member", created["invitation_code"])

        with self.connect() as connection:
            membership = connection.execute(
                "SELECT role,status FROM family_memberships "
                "WHERE owner_subject_id=%s AND member_subject_id=%s",
                ("family-owner", "family-member"),
            ).fetchone()
        self.assertEqual(tuple(membership), ("member", "active"))

    def test_concurrent_postgres_pairing_approval_enforces_family_member_limit(self) -> None:
        self.store.create_user("family-owner", "family-owner@example.test", "owner-password")
        self.store.create_user("family-member", "family-member@example.test", "member-password")
        self.store.trust_device("family-member", "existing-family-device")
        subscriptions = self._create_family_subscription()
        families = FamilyMembershipRepository(self.connect, placeholder="%s")
        created_at = datetime.now(timezone.utc).isoformat()
        families.create_household("family-owner", created_at=created_at)
        families.add_member("family-owner", "family-member", created_at=created_at)

        resolver = StoreDeviceAllowanceResolver(
            self.connect, subscriptions, families, placeholder="%s"
        )
        service = PersistentIdentityService(
            self.store, device_allowance_resolver=resolver
        )
        session = service.sign_in(SignInRequest(
            "family-member@example.test", "member-password", "existing-family-device"
        ))
        pairing = service.device_pairing
        requests = [
            pairing.start(
                "family-member@example.test",
                "member-password",
                f"new-family-device-{index}",
                f"Family device {index}",
            )
            for index in range(2)
        ]

        def approve(request):
            try:
                pairing.approve(
                    session, request["request_id"],
                    pairing_code=request["pairing_code"],
                )
                return "approved"
            except DeviceLimitExceeded:
                return "limit_rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(approve, requests))

        self.assertCountEqual(outcomes, ["approved", "limit_rejected"])
        with self.connect() as connection:
            trusted_count = connection.execute(
                "SELECT COUNT(*) FROM devices WHERE subject_id=%s AND trusted=1",
                ("family-member",),
            ).fetchone()[0]
        self.assertEqual(trusted_count, 2)


if __name__ == "__main__":
    unittest.main()
