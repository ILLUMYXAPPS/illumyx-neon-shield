"""Tests for subscription-backed device allowances and family membership."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from backend.device_allowance import (
    DeviceAllowanceConfigurationError,
    FamilyMembershipRepository,
    VerifiedDeviceAllowanceResolver,
)
from backend.device_limits import DeviceLimitExceeded, DeviceLimitPolicy, DevicePackage


class DeviceAllowanceResolverTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute(
            "CREATE TABLE verified_subscriptions (subject_id TEXT, package TEXT, "
            "revoked INTEGER, expires_at TEXT, verified_at TEXT)"
        )
        self.db.execute(
            "CREATE TABLE devices (subject_id TEXT, device_hash TEXT, trusted INTEGER)"
        )
        self.db.execute(
            "CREATE TABLE family_memberships (owner_subject_id TEXT, "
            "member_subject_id TEXT, status TEXT, created_at TEXT, updated_at TEXT)"
        )
        self.resolver = VerifiedDeviceAllowanceResolver(
            placeholder="?", lock_clause=""
        )

    def tearDown(self):
        self.db.close()

    def subscription(self, subject, package, *, revoked=0, expires_at=None):
        self.db.execute(
            "INSERT INTO verified_subscriptions VALUES(?,?,?,?,?)",
            (subject, package, revoked, expires_at,
             datetime.now(timezone.utc).isoformat()),
        )
        self.db.commit()

    def devices(self, subject, count):
        existing = self.db.execute(
            "SELECT COUNT(*) FROM devices WHERE subject_id=?", (subject,)
        ).fetchone()[0]
        self.db.executemany(
            "INSERT INTO devices VALUES(?,?,1)",
            [(subject, f"{subject}-device-{i}")
             for i in range(existing, existing + count)],
        )
        self.db.commit()

    def resolve(self, subject):
        return self.resolver.resolve_in_transaction(self.db.cursor(), subject)

    def test_premium_uses_verified_subscription_and_counts_trusted_devices(self):
        self.subscription("owner", "premium")
        self.devices("owner", 2)
        allowance = self.resolve("owner")
        self.assertEqual(allowance.package, DevicePackage.PREMIUM)
        self.assertEqual(allowance.member_device_count, 2)
        DeviceLimitPolicy.assert_can_add_device(allowance)

        self.devices("owner", 1)
        with self.assertRaises(DeviceLimitExceeded):
            DeviceLimitPolicy.assert_can_add_device(self.resolve("owner"))

    def test_expired_or_revoked_subscription_falls_back_to_free(self):
        expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.subscription("expired", "premium", expires_at=expired)
        self.subscription("revoked", "premium", revoked=1)
        self.assertEqual(self.resolve("expired").package, DevicePackage.FREE)
        self.assertEqual(self.resolve("revoked").package, DevicePackage.FREE)

    def test_family_member_inherits_only_active_owner_subscription(self):
        self.subscription("owner", "premium_family")
        self.db.execute(
            "INSERT INTO family_memberships VALUES(?,?,?,?,?)",
            ("owner", "member", "active", "now", "now"),
        )
        self.devices("member", 1)
        self.devices("owner", 1)
        allowance = self.resolve("member")
        self.assertEqual(allowance.package, DevicePackage.PREMIUM_FAMILY)
        self.assertEqual(allowance.member_device_count, 1)
        self.assertEqual(allowance.family_total_device_count, 2)

    def test_family_total_device_count_blocks_eleventh_device(self):
        self.subscription("owner", "premium_family")
        for index in range(4):
            member = f"member-{index}"
            self.db.execute(
                "INSERT INTO family_memberships VALUES(?,?,?,?,?)",
                ("owner", member, "active", "now", "now"),
            )
        self.db.commit()
        for subject in ["owner", "member-0", "member-1", "member-2"]:
            self.devices(subject, 2)
        self.devices("member-3", 1)
        allowance = self.resolve("member-3")
        self.assertEqual(allowance.member_device_count, 1)
        self.assertEqual(allowance.family_total_device_count, 9)
        DeviceLimitPolicy.assert_can_add_device(allowance)

        self.devices("owner", 1)
        allowance = self.resolve("member-3")
        self.assertEqual(allowance.member_device_count, 1)
        self.assertEqual(allowance.family_total_device_count, 10)
        with self.assertRaises(DeviceLimitExceeded):
            DeviceLimitPolicy.assert_can_add_device(allowance)


    def test_family_member_third_device_is_blocked(self):
        self.subscription("owner", "premium_family")
        self.db.execute(
            "INSERT INTO family_memberships VALUES(?,?,?,?,?)",
            ("owner", "member", "active", "now", "now"),
        )
        self.db.commit()
        self.devices("member", 2)
        allowance = self.resolve("member")
        self.assertEqual(allowance.member_device_count, 2)
        with self.assertRaises(DeviceLimitExceeded):
            DeviceLimitPolicy.assert_can_add_device(allowance)

    def test_inactive_membership_does_not_inherit_family_subscription(self):
        self.subscription("owner", "premium_family")
        self.db.execute(
            "INSERT INTO family_memberships VALUES(?,?,?,?,?)",
            ("owner", "removed-member", "removed", "now", "now"),
        )
        self.db.commit()
        self.assertEqual(self.resolve("removed-member").package, DevicePackage.FREE)


class FamilyMembershipRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = self.temp.name + "/family.sqlite3"
        self.db = sqlite3.connect(self.path)
        self.db.execute(
            "CREATE TABLE verified_subscriptions (subject_id TEXT, package TEXT, "
            "revoked INTEGER, expires_at TEXT, verified_at TEXT)"
        )
        self.db.execute(
            "CREATE TABLE family_memberships (owner_subject_id TEXT, "
            "member_subject_id TEXT UNIQUE, status TEXT, created_at TEXT, updated_at TEXT)"
        )
        self.db.execute(
            "INSERT INTO verified_subscriptions VALUES(?,?,?,?,?)",
            ("owner", "premium_family", 0, None,
             datetime.now(timezone.utc).isoformat()),
        )
        self.db.commit()
        self.repository = FamilyMembershipRepository(
            lambda: sqlite3.connect(self.path), placeholder="?", lock_clause=""
        )

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_add_member_requires_family_package_and_enforces_five_people(self):
        for index in range(4):
            self.repository.add_member(
                owner_subject_id="owner", member_subject_id=f"member-{index}"
            )
        with self.assertRaises(DeviceAllowanceConfigurationError):
            self.repository.add_member(
                owner_subject_id="owner", member_subject_id="member-5"
            )

    def test_member_cannot_join_two_families(self):
        self.db.execute(
            "INSERT INTO verified_subscriptions VALUES(?,?,?,?,?)",
            ("another-owner", "premium_family", 0, None,
             datetime.now(timezone.utc).isoformat()),
        )
        self.db.commit()
        self.repository.add_member(
            owner_subject_id="owner", member_subject_id="member"
        )
        with self.assertRaises(DeviceAllowanceConfigurationError):
            self.repository.add_member(
                owner_subject_id="another-owner", member_subject_id="member"
            )

    def test_remove_member_revokes_family_entitlement(self):
        self.repository.add_member(
            owner_subject_id="owner", member_subject_id="member"
        )
        self.repository.remove_member(
            owner_subject_id="owner", member_subject_id="member"
        )
        row = self.db.execute(
            "SELECT status FROM family_memberships WHERE member_subject_id='member'"
        ).fetchone()
        self.assertEqual(row[0], "removed")


if __name__ == "__main__":
    unittest.main()
