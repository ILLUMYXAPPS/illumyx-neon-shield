"""Verified Apple App Store Server Notifications V2 processing."""
from __future__ import annotations

import base64
import importlib
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
            signed_renewal = self._field(data, "signedRenewalInfo")
            if signed_renewal:
                renewal = self._verifier.verify_signed_notification_renewal(
                    signed_renewal
                )
                renewal_original = self._field(renewal, "originalTransactionId")
                renewal_product = self._field(renewal, "productId")
                if (renewal_original != verified.original_transaction_id
                        or renewal_product != verified.product_id):
                    raise StoreVerificationError(
                        "Apple signed renewal information does not match its transaction"
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



class GoogleRtdnProcessor:
    """Authenticate Google Pub/Sub OIDC delivery and reconcile RTDN via Play API."""

    def __init__(self, *, verifier, verification_service, subscription_repository,
                 account_binding_repository, package_name: str, audience: str,
                 service_account_email: str, token_verifier=None) -> None:
        if not all((verifier, verification_service, subscription_repository,
                    account_binding_repository, package_name, audience,
                    service_account_email)):
            raise ValueError("Google RTDN configuration is incomplete")
        self._verifier = verifier
        self._verification = verification_service
        self._subscriptions = subscription_repository
        self._bindings = account_binding_repository
        self._package_name = package_name
        self._audience = audience
        self._service_account_email = service_account_email
        self._token_verifier = token_verifier or self._verify_google_oidc

    def _verify_google_oidc(self, token: str, audience: str) -> dict:
        try:
            request_module = importlib.import_module("google.auth.transport.requests")
            token_module = importlib.import_module("google.oauth2.id_token")
            return token_module.verify_oauth2_token(
                token, request_module.Request(), audience
            )
        except Exception as exc:
            raise StoreVerificationError("Google Pub/Sub OIDC token is invalid") from exc

    def process(self, authorization: str, envelope: dict, *, received_at=None) -> bool:
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise StoreVerificationError("Google Pub/Sub bearer token is required")
        token = authorization[7:].strip()
        if not token:
            raise StoreVerificationError("Google Pub/Sub bearer token is required")
        claims = self._token_verifier(token, self._audience)
        if (claims.get("email") != self._service_account_email
                or claims.get("email_verified") is not True
                or claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}
                or claims.get("aud") != self._audience):
            raise StoreVerificationError("Google Pub/Sub OIDC identity is not authorized")

        message = envelope.get("message") if isinstance(envelope, dict) else None
        if not isinstance(message, dict):
            raise StoreVerificationError("Google Pub/Sub message is missing")
        event_id = message.get("messageId")
        encoded = message.get("data")
        if not event_id or not encoded:
            raise StoreVerificationError("Google Pub/Sub message identity or data is missing")
        try:
            payload = json.loads(base64.b64decode(encoded, validate=True))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise StoreVerificationError("Google RTDN message data is invalid") from exc
        if not isinstance(payload, dict) or payload.get("packageName") != self._package_name:
            raise StoreVerificationError("Google RTDN package name mismatch")

        notification = payload.get("subscriptionNotification") or {}
        purchase_token = notification.get("purchaseToken")
        product_id = notification.get("subscriptionId")
        if purchase_token or product_id:
            if not purchase_token or not product_id:
                raise StoreVerificationError("Google RTDN subscription details are incomplete")
            request = self._verifier.request_from_notification(
                package_name=self._package_name,
                product_id=str(product_id),
                purchase_token=str(purchase_token),
            )
            subject_id = self._bindings.get_subject_for_binding(request.account_binding_id)
            if not subject_id:
                raise StoreVerificationError("Google RTDN account binding is not associated with a Neon Shield account")
            self._verification.verify_and_persist(
                request,
                subject_id=subject_id,
                expected_account_binding_id=request.account_binding_id,
                repository=self._subscriptions,
                now=received_at,
            )

        event_type = str(notification.get("notificationType", "TEST" if payload.get("testNotification") else "UNKNOWN"))
        inserted = self._subscriptions.record_notification(
            provider=StoreProvider.GOOGLE_PLAY,
            event_id=str(event_id),
            event_type=event_type,
            payload=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            received_at=received_at or datetime.now(timezone.utc),
        )
        if inserted:
            finalized = self._subscriptions.finish_notification(
                provider=StoreProvider.GOOGLE_PLAY,
                event_id=str(event_id),
                processed=True,
                processed_at=received_at or datetime.now(timezone.utc),
            )
            if not finalized:
                raise StoreVerificationError("Google RTDN event could not be finalized")
        return inserted
