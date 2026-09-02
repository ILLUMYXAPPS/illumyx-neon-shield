"""Regression tests for server-authoritative package entitlements."""

from datetime import datetime, timedelta, timezone
import unittest

from entitlements import EntitlementPolicy, Feature, Package, SubscriptionSnapshot


class EntitlementPolicyTests(unittest.TestCase):
    NOW = datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc)

    def test_free_gets_core_but_not_premium_features(self):
        snapshot = SubscriptionSnapshot(Package.FREE, active=True)
        self.assertTrue(EntitlementPolicy.allows(snapshot, Feature.CORE_SECURITY, now=self.NOW))
        self.assertFalse(
            EntitlementPolicy.allows(
                snapshot, Feature.TRUSTED_DEVICE_MANAGEMENT, now=self.NOW
            )
        )

    def test_active_premium_gets_premium_features(self):
        snapshot = SubscriptionSnapshot(Package.PREMIUM, active=True)
        self.assertTrue(
            EntitlementPolicy.allows(
                snapshot, Feature.SECURITY_ALERTS, now=self.NOW
            )
        )
        self.assertFalse(
            EntitlementPolicy.allows(snapshot, Feature.FAMILY_PROTECTION, now=self.NOW)
        )

    def test_active_family_gets_premium_and_family_features(self):
        snapshot = SubscriptionSnapshot(
            Package.PREMIUM_FAMILY, active=True, family_member_count=5
        )
        self.assertTrue(
            EntitlementPolicy.allows(
                snapshot, Feature.SECURITY_AUDIT_HISTORY, now=self.NOW
            )
        )
        self.assertTrue(
            EntitlementPolicy.allows(snapshot, Feature.FAMILY_PROTECTION, now=self.NOW)
        )

    def test_expired_subscription_fails_closed(self):
        snapshot = SubscriptionSnapshot(
            Package.PREMIUM,
            active=True,
            expires_at=self.NOW - timedelta(seconds=1),
        )
        self.assertFalse(
            EntitlementPolicy.allows(snapshot, Feature.SECURITY_ALERTS, now=self.NOW)
        )

    def test_inactive_subscription_fails_closed(self):
        snapshot = SubscriptionSnapshot(Package.PREMIUM, active=False)
        self.assertFalse(
            EntitlementPolicy.allows(snapshot, Feature.SECURITY_ALERTS, now=self.NOW)
        )

    def test_family_limit_is_five(self):
        snapshot = SubscriptionSnapshot(
            Package.PREMIUM_FAMILY, active=True, family_member_count=5
        )
        self.assertTrue(
            EntitlementPolicy.family_member_allowed(
                snapshot, member_number=5, now=self.NOW
            )
        )
        self.assertFalse(
            EntitlementPolicy.family_member_allowed(
                snapshot, member_number=6, now=self.NOW
            )
        )

    def test_family_member_count_cannot_exceed_declared_limit(self):
        snapshot = SubscriptionSnapshot(
            Package.PREMIUM_FAMILY, active=True, family_member_count=8
        )
        self.assertFalse(
            EntitlementPolicy.family_member_allowed(
                snapshot, member_number=6, now=self.NOW
            )
        )

    def test_non_family_package_cannot_claim_family_members(self):
        with self.assertRaises(ValueError):
            SubscriptionSnapshot(Package.PREMIUM, active=True, family_member_count=1)

    def test_expiry_boundary_is_fail_closed(self):
        snapshot = SubscriptionSnapshot(
            Package.PREMIUM, active=True, expires_at=self.NOW
        )
        self.assertFalse(
            EntitlementPolicy.allows(snapshot, Feature.SECURITY_ALERTS, now=self.NOW)
        )


if __name__ == "__main__":
    unittest.main()
