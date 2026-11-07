"""Security tests for consent-based, one-time Family invitations."""
from __future__ import annotations

import sqlite3
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.family_invitations import FamilyInvitationError, FamilyInvitationService
from backend.device_allowance import FamilyMembershipRepository
from backend.migrations import MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS
from backend.subscription_store import StoreSubscriptionRepository


NOW = "2026-11-08T00:00:00+00:00"


class FamilyInvitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.connections = []
        self.addCleanup(self._close_connections)
        self.path = Path(self.tmp.name) / "family-invitations.sqlite3"

        def connect():
            connection = sqlite3.connect(self.path, timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            self.connections.append(connection)
            return connection

        self.connect = connect
        MigrationRunner(self.connect, PRODUCTION_MIGRATIONS).apply_pending()
        with self.connect() as connection:
            for subject in ("owner", "member-1", "member-2", "member-3", "member-4", "member-5", "other-owner"):
                connection.execute(
                    "INSERT INTO users(subject_id,identity_hash,credential_record,created_at) VALUES(?,?,?,?)",
                    (subject, "hash-" + subject, "credential", NOW),
                )
            connection.execute(
                "INSERT INTO verified_subscriptions "
                "(subscription_id,subject_id,provider,application_id,product_id,package,environment,"
                "account_binding_id,transaction_id,original_transaction_id,purchase_token_hash,"
                "expires_at,revoked,verified_at,updated_at) "
                "VALUES('family-owner','owner','apple','com.illumyx.illumyxapp','family_monthly',"
                "'premium_family','production','binding-owner','txn-owner','original-owner','token-hash',"
                "NULL,0,?,?)",
                (NOW, NOW),
            )
            connection.commit()
        self.subscriptions = StoreSubscriptionRepository(
            self.connect, pepper="family-invitation-test-pepper", placeholder="?"
        )
        self.invitations = FamilyInvitationService(
            self.connect, self.subscriptions, placeholder="?"
        )

    def _close_connections(self):
        for connection in self.connections:
            try:
                connection.close()
            except sqlite3.Error:
                pass

    def test_owner_creates_hashed_one_time_invitation_and_recipient_accepts(self):
        created = self.invitations.create_invitation("owner")
        self.assertEqual(len(created["invitation_code"]), 43)
        with self.connect() as connection:
            row = connection.execute(
                "SELECT token_hash,status FROM family_invitations WHERE invitation_id=?",
                (created["invitation_id"],),
            ).fetchone()
            self.assertNotEqual(row["token_hash"], created["invitation_code"])
            self.assertEqual(row["status"], "pending")
        self.assertEqual(
            self.invitations.accept_invitation("member-1", created["invitation_code"]),
            {"status": "accepted"},
        )
        with self.connect() as connection:
            membership = connection.execute(
                "SELECT role,status FROM family_memberships WHERE owner_subject_id='owner' AND member_subject_id='member-1'"
            ).fetchone()
            invite = connection.execute(
                "SELECT status,accepted_by FROM family_invitations WHERE invitation_id=?",
                (created["invitation_id"],),
            ).fetchone()
        self.assertEqual(tuple(membership), ("member", "active"))
        self.assertEqual(tuple(invite), ("accepted", "member-1"))
        with self.assertRaises(FamilyInvitationError):
            self.invitations.accept_invitation("member-2", created["invitation_code"])

    def test_two_recipients_cannot_consume_the_same_invitation_concurrently(self):
        created = self.invitations.create_invitation("owner")
        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()

        def accept(member):
            barrier.wait(timeout=5)
            try:
                self.invitations.accept_invitation(member, created["invitation_code"])
                result = "accepted"
            except FamilyInvitationError:
                result = "rejected"
            with lock:
                outcomes.append((member, result))

        threads = [
            threading.Thread(target=accept, args=("member-1",)),
            threading.Thread(target=accept, args=("member-2",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual([result for _, result in outcomes].count("accepted"), 1)
        self.assertEqual([result for _, result in outcomes].count("rejected"), 1)
        with self.connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM family_memberships WHERE owner_subject_id='owner' AND role='member' AND status='active'"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_owner_can_list_pending_invitation_metadata_without_secret_codes(self):
        created = self.invitations.create_invitation("owner")
        listed = self.invitations.list_invitations("owner")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["invitation_id"], created["invitation_id"])
        self.assertNotIn("invitation_code", listed[0])
        self.assertNotIn("token_hash", listed[0])
        self.assertEqual(self.invitations.list_invitations("member-1"), ())

    def test_invitation_requires_verified_active_family_subscription(self):
        with self.connect() as connection:
            connection.execute("UPDATE verified_subscriptions SET revoked=1 WHERE subject_id='owner'")
            connection.commit()
        with self.assertRaisesRegex(FamilyInvitationError, "active_premium_family_required"):
            self.invitations.create_invitation("owner")

    def test_pending_invitations_reserve_the_four_available_family_places(self):
        invitations = [
            self.invitations.create_invitation("owner")
            for _ in range(4)
        ]
        self.assertEqual(len(invitations), 4)
        with self.assertRaisesRegex(FamilyInvitationError, "family_member_limit_reached"):
            self.invitations.create_invitation("owner")

    def test_invitation_can_be_revoked_only_by_owner_and_then_cannot_be_used(self):
        created = self.invitations.create_invitation("owner")
        self.assertFalse(
            self.invitations.revoke_invitation("member-1", created["invitation_id"])
        )
        self.assertTrue(
            self.invitations.revoke_invitation("owner", created["invitation_id"])
        )
        with self.assertRaises(FamilyInvitationError):
            self.invitations.accept_invitation("member-1", created["invitation_code"])

    def test_recipient_cannot_join_two_family_households(self):
        created = self.invitations.create_invitation("owner")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO family_households(owner_subject_id,created_at) VALUES('other-owner',?)",
                (NOW,),
            )
            connection.execute(
                "INSERT INTO family_memberships(owner_subject_id,member_subject_id,role,status,created_at) "
                "VALUES('other-owner','member-1','owner','active',?)",
                (NOW,),
            )
            connection.commit()
        with self.assertRaisesRegex(FamilyInvitationError, "account_already_in_a_family"):
            self.invitations.accept_invitation("member-1", created["invitation_code"])

    def test_removed_member_can_reaccept_invitation_to_the_same_household(self):
        first = self.invitations.create_invitation("owner")
        self.invitations.accept_invitation("member-1", first["invitation_code"])
        memberships = FamilyMembershipRepository(self.connect, placeholder="?")
        self.assertTrue(memberships.remove_member("owner", "member-1"))
        second = self.invitations.create_invitation("owner")
        self.invitations.accept_invitation("member-1", second["invitation_code"])
        with self.connect() as connection:
            row = connection.execute(
                "SELECT status FROM family_memberships WHERE owner_subject_id='owner' AND member_subject_id='member-1'"
            ).fetchone()
        self.assertEqual(row["status"], "active")

    def test_removed_member_cannot_switch_to_a_different_household(self):
        created = self.invitations.create_invitation("owner")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO family_households(owner_subject_id,created_at) VALUES('other-owner',?)",
                (NOW,),
            )
            connection.execute(
                "INSERT INTO family_memberships(owner_subject_id,member_subject_id,role,status,created_at) "
                "VALUES('other-owner','member-1','member','removed',?)",
                (NOW,),
            )
            connection.commit()
        with self.assertRaisesRegex(FamilyInvitationError, "account_has_previous_family_membership"):
            self.invitations.accept_invitation("member-1", created["invitation_code"])

    def test_owner_cannot_accept_own_invitation(self):
        created = self.invitations.create_invitation("owner")
        with self.assertRaisesRegex(FamilyInvitationError, "owner_cannot_accept_own_invitation"):
            self.invitations.accept_invitation("owner", created["invitation_code"])

    def test_expired_invitation_is_marked_expired_and_rejected(self):
        created = self.invitations.create_invitation("owner")
        with self.connect() as connection:
            connection.execute(
                "UPDATE family_invitations SET expires_at='2020-01-01T00:00:00+00:00' WHERE invitation_id=?",
                (created["invitation_id"],),
            )
            connection.commit()
        with self.assertRaisesRegex(FamilyInvitationError, "invitation_expired"):
            self.invitations.accept_invitation("member-1", created["invitation_code"])
        with self.connect() as connection:
            status = connection.execute(
                "SELECT status FROM family_invitations WHERE invitation_id=?",
                (created["invitation_id"],),
            ).fetchone()[0]
        self.assertEqual(status, "expired")


    def test_invitation_operations_are_rate_limited_and_rejections_count(self):
        self.invitations.RATE_LIMITS["create"] = (2, 3600)
        self.invitations.create_invitation("owner")
        self.invitations.create_invitation("owner")
        with self.assertRaisesRegex(FamilyInvitationError, "family_invitation_rate_limited") as raised:
            self.invitations.create_invitation("owner")
        self.assertEqual(raised.exception.status, 429)
        with self.connect() as connection:
            row = connection.execute(
                "SELECT failure_count FROM sign_in_rate_limits WHERE identity_hash=?",
                (__import__("hashlib").sha256(b"family-invitations:create:owner").hexdigest(),),
            ).fetchone()
        self.assertEqual(row[0], 3)

    def test_successful_invitation_lifecycle_writes_hash_chained_audit_events(self):
        created = self.invitations.create_invitation("owner")
        self.invitations.accept_invitation("member-1", created["invitation_code"])
        second = self.invitations.create_invitation("owner")
        self.assertTrue(self.invitations.revoke_invitation("owner", second["invitation_id"]))
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT event_type,subject_id,device_fingerprint,previous_hash,event_hash "
                "FROM audit_events ORDER BY occurred_at,event_hash"
            ).fetchall()
        event_types = [row["event_type"] for row in rows]
        self.assertEqual(event_types, [
            "family_invitation_created",
            "family_invitation_accepted",
            "family_invitation_created",
            "family_invitation_revoked",
        ])
        for index, row in enumerate(rows):
            self.assertEqual(len(row["device_fingerprint"]), 64)
            expected_previous = rows[index - 1]["event_hash"] if index else "0" * 64
            self.assertEqual(row["previous_hash"], expected_previous)
            self.assertNotIn(created["invitation_code"], row["device_fingerprint"])


if __name__ == "__main__":
    unittest.main()
