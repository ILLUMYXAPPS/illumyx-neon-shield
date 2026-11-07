"""Tests for the Google Play Developer API subscription verifier."""
import unittest
from datetime import datetime, timedelta, timezone

from store_verification import (
    GooglePlayVerifier, StoreProvider, StorePurchaseRequest, StoreVerificationError,
)


class Request:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return self.value


class SubscriptionsV2:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        return Request(self.response)

class Subscriptions:
    def __init__(self):
        self.acknowledged = []

    def acknowledge(self, **kwargs):
        self.acknowledged.append(kwargs)
        return Request({})

class Purchases:
    def __init__(self, response):
        self.v2 = SubscriptionsV2(response)
        self.legacy = Subscriptions()

    def subscriptionsv2(self):
        return self.v2

    def subscriptions(self):
        return self.legacy

class Publisher:
    def __init__(self, response):
        self.api = Purchases(response)

    def purchases(self):
        return self.api


def response(**changes):
    values = {
        "subscriptionState": "SUBSCRIPTION_STATE_ACTIVE",
        "acknowledgementState": "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED",
        "externalAccountIdentifiers": {
            "obfuscatedExternalAccountId": "server-account-binding"
        },
        "lineItems": [{
            "productId": "premium.monthly",
            "expiryTime": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "latestSuccessfulOrderId": "GPA.order.123",
        }],
    }
    values.update(changes)
    return values


class GooglePlayVerifierTests(unittest.TestCase):
    def setUp(self):
        self.publisher = Publisher(response())
        self.verifier = GooglePlayVerifier(
            publisher_client=self.publisher, token_hash_key="deployment-secret"
        )
        self.request = StorePurchaseRequest(
            StoreProvider.GOOGLE_PLAY, "opaque-google-purchase-token",
            "premium.monthly", "com.illumyx.illumyxapp",
            "server-account-binding",
        )

    def test_active_purchase_is_verified_and_token_is_not_used_as_transaction_id(self):
        result = self.verifier.verify(self.request)
        self.assertEqual(result.provider, StoreProvider.GOOGLE_PLAY)
        self.assertEqual(result.transaction_id, "GPA.order.123")
        self.assertNotEqual(result.original_transaction_id, self.request.purchase_token)
        self.assertEqual(len(result.original_transaction_id), 64)
        self.assertEqual(result.account_binding_id, "server-account-binding")

    def test_account_binding_mismatch_rejected(self):
        self.publisher.api.v2.response["externalAccountIdentifiers"][
            "obfuscatedExternalAccountId"
        ] = "attacker-binding"
        with self.assertRaisesRegex(StoreVerificationError, "obfuscatedExternalAccountId"):
            self.verifier.verify(self.request)

    def test_wrong_product_rejected(self):
        self.publisher.api.v2.response["lineItems"][0]["productId"] = "other.product"
        with self.assertRaisesRegex(StoreVerificationError, "product"):
            self.verifier.verify(self.request)

    def test_pending_or_on_hold_subscription_rejected(self):
        self.publisher.api.v2.response["subscriptionState"] = "SUBSCRIPTION_STATE_ON_HOLD"
        with self.assertRaisesRegex(StoreVerificationError, "not entitled"):
            self.verifier.verify(self.request)

    def test_on_hold_subscription_is_returned_as_revoked_for_reconciliation(self):
        self.publisher.api.v2.response["subscriptionState"] = "SUBSCRIPTION_STATE_ON_HOLD"
        result = self.verifier.verify(self.request)
        self.assertTrue(result.revoked)

    def test_expired_subscription_rejected(self):
        self.publisher.api.v2.response["lineItems"][0]["expiryTime"] = (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).isoformat()
        with self.assertRaisesRegex(StoreVerificationError, "expired"):
            self.verifier.verify(self.request)

    def test_pending_acknowledgement_is_acknowledged_server_side(self):
        self.publisher.api.v2.response["acknowledgementState"] = "ACKNOWLEDGEMENT_STATE_PENDING"
        def acknowledge(**kwargs):
            self.publisher.api.v2.response["acknowledgementState"] = "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"
            return Request({})
        self.publisher.api.legacy.acknowledge = acknowledge
        result = self.verifier.verify(self.request)
        self.assertFalse(result.revoked)
        self.assertEqual(len(self.publisher.api.legacy.acknowledged), 1)
        self.assertEqual(self.publisher.api.legacy.acknowledged[0]["subscriptionId"], "premium.monthly")

    def test_api_failure_fails_closed(self):
        class BrokenV2:
            def get(self, **kwargs):
                return Request(error=RuntimeError("network"))
        self.publisher.api.v2 = BrokenV2()
        with self.assertRaisesRegex(StoreVerificationError, "lookup failed"):
            self.verifier.verify(self.request)


if __name__ == "__main__":
    unittest.main()
