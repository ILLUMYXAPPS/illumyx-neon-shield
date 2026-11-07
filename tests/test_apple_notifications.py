"""Tests for verified Apple App Store Server Notifications V2 processing."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from store_notifications import AppleNotificationProcessor
from store_verification import StoreProvider, VerifiedStorePurchase, StoreVerificationError


class AppleNotificationProcessorTests(unittest.TestCase):
    def setUp(self):
        self.purchase = VerifiedStorePurchase(
            provider=StoreProvider.APPLE,
            product_id="premium.monthly",
            application_id="com.illumyx.illumyxapp",
            account_binding_id="8e03978e-40d5-43e8-bc93-6894a57f9324",
            transaction_id="tx-1",
            original_transaction_id="original-1",
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            environment="sandbox",
        )
        self.verifier = Mock()
        self.verifier.verify_notification.return_value = SimpleNamespace(
            notificationUUID="event-1",
            notificationType="DID_RENEW",
            data=SimpleNamespace(signedTransactionInfo="signed.transaction.jws"),
        )
        self.verifier.verify_signed_notification_transaction.return_value = self.purchase
        self.verification = Mock()
        self.bindings = Mock()
        self.bindings.get_subject_for_binding.return_value = "account-1"
        self.repository = Mock()
        self.repository.record_notification.return_value = True
        self.processor = AppleNotificationProcessor(
            verifier=self.verifier,
            verification_service=self.verification,
            subscription_repository=self.repository,
            account_binding_repository=self.bindings,
        )

    def test_verifies_and_reconciles_signed_transaction_before_recording_event(self):
        result = self.processor.process("signed.notification.jws")
        self.assertTrue(result)
        self.verification.verify_and_persist.assert_called_once()
        kwargs = self.verification.verify_and_persist.call_args.kwargs
        self.assertEqual(kwargs["subject_id"], "account-1")
        self.assertEqual(self.verification.verify_and_persist.call_args.args[0].purchase_token, "signed.transaction.jws")
        self.assertEqual(kwargs["expected_account_binding_id"], self.purchase.account_binding_id)
        self.repository.record_notification.assert_called_once()
        self.assertEqual(self.repository.record_notification.call_args.kwargs["event_id"], "event-1")

    def test_duplicate_event_is_reported_after_safe_idempotent_reconciliation(self):
        self.repository.record_notification.return_value = False
        self.assertFalse(self.processor.process("signed.notification.jws"))

    def test_unknown_account_binding_rejected_without_recording_event(self):
        self.bindings.get_subject_for_binding.return_value = None
        with self.assertRaisesRegex(StoreVerificationError, "not associated"):
            self.processor.process("signed.notification.jws")
        self.repository.record_notification.assert_not_called()

    def test_missing_signed_payload_rejected(self):
        with self.assertRaisesRegex(StoreVerificationError, "signedPayload"):
            self.processor.process("")

    def test_signed_notification_without_transaction_is_stored(self):
        self.verifier.verify_notification.return_value = SimpleNamespace(
            notificationUUID="event-2", notificationType="TEST", data=None
        )
        self.assertTrue(self.processor.process("signed.test.notification"))
        self.verification.verify_and_persist.assert_not_called()
        self.repository.record_notification.assert_called_once()


if __name__ == "__main__":
    unittest.main()
