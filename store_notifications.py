"""Verified Apple App Store Server Notifications V2 processing."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from store_verification import StoreProvider, StorePurchaseRequest, StoreVerificationError


class AppleNotificationProcessor:
    """Verify Apple notification and nested transaction evidence before reconciliation.

    Processing is retry-safe: subscription persistence is idempotent on Apple's
    original transaction ID, and the notification event is recorded only after
    the signed transaction has been reconciled successfully.
    """

    def __init__(self, *, verifier, verification_service, subscription_repository,
                 account_binding_repository) -> None:
        required = (verifier, verification_service, subscription_repository,
                    account_binding_repository)
        if any(item is None for item in required):
            raise ValueError("Apple notification dependencies are required")
        self._verifier = verifier
        self._verification = verification_service
        self._subscriptions = subscription_repository
        self._bindings = account_binding_repository

    @staticmethod
    def _field(value, name, default=None):
        if isinstance(value, dict):
            return value.get(name, default)
        return getattr(value, name, default)

    def process(self, signed_payload: str, *, received_at: datetime | None = None) -> bool:
        """Return True for a newly processed event, False for an already-seen event."""
        if not isinstance(signed_payload, str) or not signed_payload.strip():
            raise StoreVerificationError("Apple signedPayload is required")
        event = self._verifier.verify_notification(signed_payload)
        event_id = self._field(event, "notificationUUID")
        event_type = self._field(event, "notificationType")
        if not event_id or not event_type:
            raise StoreVerificationError("Apple notification identity is missing")

        data = self._field(event, "data")
        signed_transaction = self._field(data, "signedTransactionInfo")
        if signed_transaction:
            verified = self._verifier.verify_signed_notification_transaction(
                signed_transaction
            )
            binding_id = verified.account_binding_id
            subject_id = self._bindings.get_subject_for_binding(binding_id)
            if not subject_id:
                raise StoreVerificationError(
                    "Apple notification account binding is not associated with a Neon Shield account"
                )
            request = StorePurchaseRequest(
                provider=StoreProvider.APPLE,
                purchase_token=signed_transaction,
                product_id=verified.product_id,
                application_id=verified.application_id,
                account_binding_id=binding_id,
            )
            # verify_and_persist re-verifies the nested JWS through the configured
            # provider adapter and persists refunds/revocations as inactive facts.
            self._verification.verify_and_persist(
                request,
                subject_id=subject_id,
                expected_account_binding_id=binding_id,
                repository=self._subscriptions,
                now=received_at,
            )

        payload_bytes = signed_payload.encode("utf-8")
        inserted = self._subscriptions.record_notification(
            provider=StoreProvider.APPLE,
            event_id=str(event_id),
            event_type=str(event_type),
            payload=payload_bytes,
            received_at=received_at or datetime.now(timezone.utc),
        )
        if inserted:
            finalized = self._subscriptions.finish_notification(
                provider=StoreProvider.APPLE,
                event_id=str(event_id),
                processed=True,
                processed_at=received_at or datetime.now(timezone.utc),
            )
            if not finalized:
                raise StoreVerificationError("Apple notification could not be finalized")
        return inserted
