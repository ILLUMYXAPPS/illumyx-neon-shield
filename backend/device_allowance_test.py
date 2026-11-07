"""Tests for trusted family membership and subscription-derived device allowances."""
from __future__ import annotations

import sqlite3
import unittest
from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from pathlib import Path

from backend.device_allowance import (
    FamilyMembershipError,
    FamilyMembershipRepository,
    StoreDeviceAllowanceResolver,
)
from backend.migrations import MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS
from entitlements import Package, SubscriptionSnapshot


NOW = datetime(2026, 11, 8, 0, 0, tzinfo=timezone.utc).isoformat()


class FakeSubscriptions:
    def __init__(self, packages):
        self.packages = packages

    def get_subscription_snapshot(self, subject_id):
        return SubscriptionSnapshot(self.packages.get(subject_id, Package.FREE), active=True)


class FamilyMembershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "family.sqlite3"

        def connect():
            connection = sqlite3.connect(self.path)
            connection.execute("PRAGMA foreign_keys=ON")
            return connection

        self.connect = connect
        MigrationRunner(self.connect, PRODUCTION_MIGRATIONS).apply_pending()
        with self.connect() as connection:
            for subject in ("owner", "member-1", "member-2", "member-3", "member-4", "member-5"):
                connection.execute(
                    "INSERT INTO users(subject_id,identity_hash,credential_record,created_at) VALUES(?,?,?,?)",
                    (subject, "hash-" + subject, "credential", NOW),
                )
        self.families = FamilyMembershipRepository(self.connect, placeholder="?")

    def test_household_owner_counts_as_one_of_five_members(self):
        self.families.create_household("owner", created_at=NOW)
        for index in range(1, 5):
            self.families.add_member("owner", f"member-{index}", created_at=NOW)
        self.assertEqual(
            set(self.families.active_members("owner")),
            {"owner", "member-1", "member-2", "member-3", "member-4"},
        )
        with self.assertRaises(FamilyMembershipError):
            self.families.add_member("owner", "member-5", created_at=NOW)

    def test_removed_member_no_longer_resolves_to_household(self):
        self.families.create_household("owner", created_at=NOW)
        self.families.add_member("owner", "member-1", created_at=NOW)
        self.assertTrue(self.families.remove_member("owner", "member-1"))
        self.assertIsNone(self.families.household_owner_for("member-1"))

    def test_family_allowance_uses_owner_subscription_and_all_household_devices(self):
        self.families.create_household("owner", created_at=NOW)
        self.families.add_member("owner", "member-1", created_at=NOW)
        with self.connect() as connection:
            for subject, count in (("owner", 2), ("member-1", 1)):
                for index in range(count):
                    connection.execute(
                        "INSERT INTO devices(subject_id,device_hash,trusted,created_at) VALUES(?,?,1,?)",
                        (subject, f"{subject}-device-{index}", NOW),
                    )
        resolver = StoreDeviceAllowanceResolver(
            self.connect,
            FakeSubscriptions({"owner": Package.PREMIUM_FAMILY}),
            self.families,
            placeholder="?",
        )
        allowance = resolver("member-1", "request-id")
        self.assertEqual(allowance.package.value, "premium_family")
        self.assertEqual(allowance.member_device_count, 1)
        self.assertEqual(allowance.family_total_device_count, 3)

    def test_family_membership_without_active_family_entitlement_falls_back_to_free(self):
        self.families.create_household("owner", created_at=NOW)
        self.families.add_member("owner", "member-1", created_at=NOW)
        resolver = StoreDeviceAllowanceResolver(
            self.connect,
            FakeSubscriptions({"owner": Package.FREE}),
            self.families,
            placeholder="?",
        )
        self.assertEqual(resolver("member-1").package.value, "free")


if __name__ == "__main__":
    unittest.main()
