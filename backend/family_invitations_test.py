"""Security tests for consent-based, one-time Family invitations."""
from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.family_invitations import FamilyInvitationError, FamilyInvitationService
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


if __name__ == "__main__":
    unittest.main()
