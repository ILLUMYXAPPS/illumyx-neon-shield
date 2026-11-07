"""Tests for authenticated Google Play Real-time Developer Notifications."""
import base64
import json
import unittest
from unittest.mock import Mock

from store_notifications import GoogleRtdnProcessor
from store_verification import StoreProvider, StorePurchaseRequest, StoreVerificationError


class FakeGoogleVerifier:
    def request_from_notification(self, *, package_name, product_id, purchase_token):
        return StorePurchaseRequest(
            StoreProvider.GOOGLE_PLAY, purchase_token, product_id,
            package_name, "server-binding",
        )


class GoogleRtdnProcessorTests(unittest.TestCase):
    def setUp(self):
        self.verifier = FakeGoogleVerifier()
        self.verification = Mock()
        self.bindings = Mock()
        self.bindings.get_subject_for_binding.return_value = "subject-1"
        self.repository = Mock()
        self.repository.record_notification.return_value = True
        self.claims = {
            "email": "rtdn@example.iam.gserviceaccount.com",
            "email_verified": True,
            "iss": "https://accounts.google.com",
            "aud": "https://neon.example/v1/store/google/rtdn",
        }
        self.processor = GoogleRtdnProcessor(
            verifier=self.verifier,
            verification_service=self.verification,
            subscription_repository=self.repository,
            account_binding_repository=self.bindings,
            package_name="com.illumyx.illumyxapp",
            audience="https://neon.example/v1/store/google/rtdn",
            service_account_email="rtdn@example.iam.gserviceaccount.com",
            token_verifier=lambda token, audience: self.claims,
        )

    def envelope(self, payload, message_id="message-1"):
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        return {"message": {"messageId": message_id, "data": encoded}}

    def test_authenticated_rtdn_reconciles_purchase_and_records_event(self):
        payload = {
            "packageName": "com.illumyx.illumyxapp",
            "subscriptionNotification": {
                "notificationType": 2,
                "purchaseToken": "google-token",
                "subscriptionId": "premium.monthly",
            },
        }
        result = self.processor.process(
            "Bearer verified-oidc-token", self.envelope(payload)
        )
        self.assertTrue(result)
        self.verification.verify_and_persist.assert_called_once()
        self.assertEqual(
            self.verification.verify_and_persist.call_args.kwargs["subject_id"],
            "subject-1",
        )
        self.repository.record_notification.assert_called_once()

    def test_wrong_oidc_identity_is_rejected(self):
        self.claims["email"] = "attacker@example.com"
        payload = {"packageName": "com.illumyx.illumyxapp", "testNotification": {}}
        with self.assertRaisesRegex(StoreVerificationError, "not authorized"):
            self.processor.process("Bearer token", self.envelope(payload))

    def test_wrong_package_is_rejected(self):
        payload = {"packageName": "com.attacker.app", "testNotification": {}}
        with self.assertRaisesRegex(StoreVerificationError, "package name mismatch"):
            self.processor.process("Bearer token", self.envelope(payload))

    def test_missing_authorization_is_rejected(self):
        with self.assertRaisesRegex(StoreVerificationError, "bearer token"):
            self.processor.process("", self.envelope({"packageName": "com.illumyx.illumyxapp"}))

    def test_test_notification_is_authenticated_and_recorded(self):
        payload = {"packageName": "com.illumyx.illumyxapp", "testNotification": {}}
        self.assertTrue(self.processor.process("Bearer token", self.envelope(payload)))
        self.verification.verify_and_persist.assert_not_called()
        self.repository.record_notification.assert_called_once()

    def test_unknown_account_binding_is_rejected(self):
        self.bindings.get_subject_for_binding.return_value = None
        payload = {
            "packageName": "com.illumyx.illumyxapp",
            "subscriptionNotification": {
                "notificationType": 2, "purchaseToken": "google-token",
                "subscriptionId": "premium.monthly",
            },
        }
        with self.assertRaisesRegex(StoreVerificationError, "not associated"):
            self.processor.process("Bearer token", self.envelope(payload))
        self.repository.record_notification.assert_not_called()


if __name__ == "__main__":
    unittest.main()
