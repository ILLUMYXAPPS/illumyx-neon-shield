"""Tests for the Apple StoreKit 2 signed transaction adapter."""
from types import SimpleNamespace
import unittest

from store_verification import (
    AppleStoreKitVerifier, StoreProvider, StorePurchaseRequest,
    StoreVerificationError,
)

ACCOUNT = "8e03978e-40d5-43e8-bc93-6894a57f9324"


class FakeAppleVerifier:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = 0

    def verify_and_decode_signed_transaction(self, signed_transaction):
        self.calls += 1
        if self.error:
            raise self.error
        return self.payload

    def verify_and_decode_notification(self, signed_payload):
        self.calls += 1
        if self.error:
            raise self.error
        return self.payload


def apple_payload(**changes):
    values = {
        "appAccountToken": ACCOUNT,
        "bundleId": "com.illumyx.illumyxapp",
        "productId": "premium.monthly",
        "transactionId": "tx-100",
        "originalTransactionId": "original-100",
        "expiresDate": 1_800_000_000_000,
        "revocationDate": None,
    }
    values.update(changes)
    return SimpleNamespace(**values)


class AppleStoreKitVerifierTests(unittest.TestCase):
    def setUp(self):
        self.request = StorePurchaseRequest(
            StoreProvider.APPLE, "eyJhbGciOiJFUzI1NiJ9.payload.signature",
            "premium.monthly", "com.illumyx.illumyxapp", ACCOUNT,
        )
        self.production = FakeAppleVerifier(error=ValueError("wrong environment"))
        self.sandbox = FakeAppleVerifier(payload=apple_payload())
        self.verifier = AppleStoreKitVerifier(
            production_verifier=self.production,
            sandbox_verifier=self.sandbox,
        )

    def test_valid_signed_transaction_maps_verified_fields(self):
        result = self.verifier.verify(self.request)
        self.assertIs(result.provider, StoreProvider.APPLE)
        self.assertEqual(result.product_id, "premium.monthly")
        self.assertEqual(result.application_id, "com.illumyx.illumyxapp")
        self.assertEqual(result.account_binding_id, ACCOUNT)
        self.assertEqual(result.transaction_id, "tx-100")
        self.assertEqual(result.original_transaction_id, "original-100")
        self.assertEqual(result.environment, "sandbox")
        self.assertFalse(result.revoked)
        self.assertEqual(self.production.calls, 1)
        self.assertEqual(self.sandbox.calls, 1)

    def test_invalid_signature_in_both_environments_fails_closed(self):
        verifier = AppleStoreKitVerifier(
            production_verifier=FakeAppleVerifier(error=ValueError("invalid")),
            sandbox_verifier=FakeAppleVerifier(error=ValueError("invalid")),
        )
        with self.assertRaisesRegex(StoreVerificationError, "signature"):
            verifier.verify(self.request)

    def test_account_binding_mismatch_rejected(self):
        self.sandbox.payload = apple_payload(appAccountToken="different-account")
        with self.assertRaisesRegex(StoreVerificationError, "appAccountToken"):
            self.verifier.verify(self.request)

    def test_wrong_bundle_rejected(self):
        self.sandbox.payload = apple_payload(bundleId="com.attacker.app")
        with self.assertRaisesRegex(StoreVerificationError, "bundle"):
            self.verifier.verify(self.request)

    def test_wrong_product_rejected(self):
        self.sandbox.payload = apple_payload(productId="other.product")
        with self.assertRaisesRegex(StoreVerificationError, "product"):
            self.verifier.verify(self.request)

    def test_revoked_transaction_is_marked_revoked(self):
        self.sandbox.payload = apple_payload(revocationDate=1_700_000_000_000)
        self.assertTrue(self.verifier.verify(self.request).revoked)

    def test_signed_notification_envelope_is_verified(self):
        self.sandbox.payload = {"notificationUUID": "event-1"}
        result = self.verifier.verify_notification("signed-notification-jws")
        self.assertEqual(result, {"notificationUUID": "event-1"})

    def test_invalid_notification_signature_fails_closed(self):
        verifier = AppleStoreKitVerifier(
            production_verifier=FakeAppleVerifier(error=ValueError("invalid")),
            sandbox_verifier=FakeAppleVerifier(error=ValueError("invalid")),
        )
        with self.assertRaisesRegex(StoreVerificationError, "notification signature"):
            verifier.verify_notification("signed-notification-jws")

    def test_non_apple_request_rejected(self):
        request = StorePurchaseRequest(
            StoreProvider.GOOGLE_PLAY, "token", "premium.monthly",
            "com.illumyx.illumyxapp", ACCOUNT,
        )
        with self.assertRaisesRegex(StoreVerificationError, "non-Apple"):
            self.verifier.verify(request)

    def test_malformed_jws_rejected_before_library(self):
        request = StorePurchaseRequest(
            StoreProvider.APPLE, "not-a-jws", "premium.monthly",
            "com.illumyx.illumyxapp", ACCOUNT,
        )
        with self.assertRaisesRegex(StoreVerificationError, "JWS"):
            self.verifier.verify(request)


if __name__ == "__main__":
    unittest.main()
