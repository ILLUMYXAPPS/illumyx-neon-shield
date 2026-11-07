"""Tests for the fail-closed store verification boundary."""
from datetime import datetime, timedelta, timezone
import unittest

from entitlements import Package
from store_verification import (StoreProduct, StoreProvider, StorePurchaseRequest,
    StoreVerificationError, StoreVerificationService, StoreVerificationUnavailable,
    VerifiedStorePurchase)

NOW = datetime(2026, 11, 7, 10, 0, tzinfo=timezone.utc)
ACCOUNT = "server-account-binding"

class StubVerifier:
    def __init__(self, purchase): self.purchase = purchase; self.calls = 0
    def verify(self, request): self.calls += 1; return self.purchase

class StoreVerificationTests(unittest.TestCase):
    def setUp(self):
        self.request = StorePurchaseRequest(StoreProvider.APPLE, "opaque-token",
            "premium.monthly", "com.illumyx.illumyxapp", ACCOUNT)
        self.purchase = VerifiedStorePurchase(StoreProvider.APPLE, "premium.monthly",
            "com.illumyx.illumyxapp", ACCOUNT, "tx-1", "original-1", NOW + timedelta(days=30),
            environment="sandbox")
        self.verifier = StubVerifier(self.purchase)
        self.products = (StoreProduct(StoreProvider.APPLE, "premium.monthly",
            "com.illumyx.illumyxapp", Package.PREMIUM),)

    def service(self, verifier=None):
        return StoreVerificationService(apple_verifier=verifier, products=self.products)

    def test_verified_purchase_grants_mapped_package(self):
        snapshot = self.service(self.verifier).verify(self.request, expected_account_binding_id=ACCOUNT, now=NOW)
        self.assertIs(snapshot.package, Package.PREMIUM)
        self.assertTrue(snapshot.active)

    def test_missing_live_verifier_fails_closed(self):
        with self.assertRaises(StoreVerificationUnavailable):
            self.service().verify(self.request, expected_account_binding_id=ACCOUNT, now=NOW)

    def test_client_account_mismatch_rejected_before_provider_call(self):
        bad = StorePurchaseRequest(StoreProvider.APPLE, "token", "premium.monthly",
            "com.illumyx.illumyxapp", "attacker-account")
        with self.assertRaises(StoreVerificationError):
            self.service(self.verifier).verify(bad, expected_account_binding_id=ACCOUNT, now=NOW)
        self.assertEqual(self.verifier.calls, 0)

    def test_unknown_product_rejected(self):
        bad = StorePurchaseRequest(StoreProvider.APPLE, "token", "client-premium",
            "com.illumyx.illumyxapp", ACCOUNT)
        with self.assertRaises(StoreVerificationError):
            self.service(self.verifier).verify(bad, expected_account_binding_id=ACCOUNT, now=NOW)

    def test_wrong_app_id_rejected(self):
        bad = StorePurchaseRequest(StoreProvider.APPLE, "token", "premium.monthly", "wrong.bundle", ACCOUNT)
        with self.assertRaises(StoreVerificationError):
            self.service(self.verifier).verify(bad, expected_account_binding_id=ACCOUNT, now=NOW)

    def test_revoked_purchase_rejected(self):
        revoked = VerifiedStorePurchase(StoreProvider.APPLE, "premium.monthly",
            "com.illumyx.illumyxapp", ACCOUNT, "tx-2", "original-2", NOW, revoked=True)
        with self.assertRaises(StoreVerificationError):
            self.service(StubVerifier(revoked)).verify(self.request, expected_account_binding_id=ACCOUNT, now=NOW)

    def test_expired_purchase_is_inactive(self):
        expired = VerifiedStorePurchase(StoreProvider.APPLE, "premium.monthly",
            "com.illumyx.illumyxapp", ACCOUNT, "tx-3", "original-3", NOW - timedelta(seconds=1))
        snapshot = self.service(StubVerifier(expired)).verify(self.request, expected_account_binding_id=ACCOUNT, now=NOW)
        self.assertFalse(snapshot.active)

if __name__ == "__main__": unittest.main()
