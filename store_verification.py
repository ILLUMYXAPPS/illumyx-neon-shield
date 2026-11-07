"""Fail-closed boundary for direct Apple App Store and Google Play verification."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Protocol

from entitlements import Package, SubscriptionSnapshot


class StoreProvider(str, Enum):
    APPLE = "apple"
    GOOGLE_PLAY = "google_play"


class StoreVerificationError(RuntimeError):
    """Purchase evidence failed server-side verification."""


class StoreVerificationUnavailable(StoreVerificationError):
    """No live store verifier is configured; paid access fails closed."""


@dataclass(frozen=True)
class StorePurchaseRequest:
    provider: StoreProvider
    purchase_token: str
    product_id: str
    application_id: str
    account_binding_id: str


@dataclass(frozen=True)
class VerifiedStorePurchase:
    provider: StoreProvider
    product_id: str
    application_id: str
    account_binding_id: str
    transaction_id: str
    original_transaction_id: str
    expires_at: datetime | None
    revoked: bool = False
    environment: str = "production"

    def __post_init__(self) -> None:
        required = (
            self.product_id,
            self.application_id,
            self.account_binding_id,
            self.transaction_id,
            self.original_transaction_id,
        )
        if any(not value or not value.strip() for value in required):
            raise ValueError("verified purchase identifiers must be non-empty")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expiry must be timezone-aware")
        if self.environment.lower() not in {"production", "sandbox"}:
            raise ValueError("environment must be production or sandbox")


class StoreVerifier(Protocol):
    def verify(self, request: StorePurchaseRequest) -> VerifiedStorePurchase:
        """Return facts only after cryptographic/API verification with the store."""
        ...



class AppleStoreKitVerifier:
    """Verify StoreKit 2 transaction JWS with Apple's official server library.

    Supply separate production and sandbox SignedDataVerifier instances. Root
    certificates must come from Apple's PKI and be provisioned by deployment.
    The library's online certificate checks are enabled by the factory below.
    """

    def __init__(self, *, production_verifier, sandbox_verifier) -> None:
        if production_verifier is None or sandbox_verifier is None:
            raise ValueError("Apple production and sandbox verifiers are required")
        self._verifiers = (production_verifier, sandbox_verifier)

    @classmethod
    def from_root_certificates(
        cls, *, root_certificates: list[bytes], bundle_id: str,
        app_apple_id: int, enable_online_checks: bool = True,
    ) -> "AppleStoreKitVerifier":
        if not root_certificates or any(not isinstance(item, bytes) or not item for item in root_certificates):
            raise ValueError("Apple root certificates must be supplied as non-empty bytes")
        if not bundle_id or not bundle_id.strip() or not isinstance(app_apple_id, int) or app_apple_id <= 0:
            raise ValueError("Apple bundle ID and numeric App Store app ID are required")
        try:
            from appstoreserverlibrary.models.Environment import Environment
            from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
        except ImportError as exc:
            raise StoreVerificationUnavailable(
                "install the Apple app-store-server-library dependency"
            ) from exc
        return cls(
            production_verifier=SignedDataVerifier(
                root_certificates, enable_online_checks, Environment.PRODUCTION,
                bundle_id, app_apple_id,
            ),
            sandbox_verifier=SignedDataVerifier(
                root_certificates, enable_online_checks, Environment.SANDBOX,
                bundle_id, None,
            ),
        )

    def verify_notification(self, signed_payload: str):
        """Cryptographically verify an App Store Server Notifications V2 envelope."""
        if not signed_payload or not signed_payload.strip():
            raise StoreVerificationError("Apple signed notification payload is required")
        last_error = None
        for verifier in self._verifiers:
            try:
                return verifier.verify_and_decode_notification(signed_payload)
            except Exception as exc:
                last_error = exc
        raise StoreVerificationError("Apple notification signature or certificate chain is invalid") from last_error

    def verify_signed_notification_transaction(self, signed_transaction: str) -> VerifiedStorePurchase:
        """Verify a nested Notifications V2 transaction JWS without trusting its claims."""
        if not signed_transaction or signed_transaction.count(".") != 2:
            raise StoreVerificationError("Apple notification transaction JWS is malformed")
        decoded = None
        environment = None
        last_error = None
        for candidate, label in zip(self._verifiers, ("production", "sandbox")):
            try:
                decoded = candidate.verify_and_decode_signed_transaction(signed_transaction)
                environment = label
                break
            except Exception as exc:
                last_error = exc
        if decoded is None:
            raise StoreVerificationError("Apple notification transaction signature is invalid") from last_error
        account_token = getattr(decoded, "appAccountToken", None)
        transaction_id = getattr(decoded, "transactionId", None)
        original_id = getattr(decoded, "originalTransactionId", None)
        product_id = getattr(decoded, "productId", None)
        bundle_id = getattr(decoded, "bundleId", None)
        expires_ms = getattr(decoded, "expiresDate", None)
        if not all((account_token, transaction_id, original_id, product_id, bundle_id)):
            raise StoreVerificationError("Apple notification transaction identifiers are missing")
        if expires_ms is None:
            raise StoreVerificationError("Apple notification subscription expiry is missing")
        try:
            import uuid
            uuid.UUID(str(account_token))
        except (ValueError, TypeError, AttributeError) as exc:
            raise StoreVerificationError("Apple appAccountToken is invalid") from exc
        return VerifiedStorePurchase(
            provider=StoreProvider.APPLE,
            product_id=str(product_id),
            application_id=str(bundle_id),
            account_binding_id=str(account_token),
            transaction_id=str(transaction_id),
            original_transaction_id=str(original_id),
            expires_at=datetime.fromtimestamp(expires_ms / 1000, tz=timezone.utc),
            revoked=(getattr(decoded, "revocationDate", None) is not None
                     or getattr(decoded, "isUpgraded", False) is True),
            environment=environment,
        )

    def verify(self, request: StorePurchaseRequest) -> VerifiedStorePurchase:
        if request.provider is not StoreProvider.APPLE:
            raise StoreVerificationError("Apple verifier received a non-Apple purchase")
        if not request.purchase_token or request.purchase_token.count(".") != 2:
            raise StoreVerificationError("StoreKit 2 signed transaction JWS is required")
        decoded = None
        environment = None
        last_error = None
        for candidate, label in zip(self._verifiers, ("production", "sandbox")):
            try:
                decoded = candidate.verify_and_decode_signed_transaction(request.purchase_token)
                environment = label
                break
            except Exception as exc:
                last_error = exc
        if decoded is None:
            raise StoreVerificationError("Apple transaction signature or certificate chain is invalid") from last_error

        account_token = getattr(decoded, "appAccountToken", None)
        if account_token is None or str(account_token).lower() != request.account_binding_id.lower():
            raise StoreVerificationError("Apple appAccountToken does not match authenticated account")
        if getattr(decoded, "bundleId", None) != request.application_id:
            raise StoreVerificationError("Apple bundle identifier mismatch")
        if getattr(decoded, "productId", None) != request.product_id:
            raise StoreVerificationError("Apple product identifier mismatch")
        transaction_id = getattr(decoded, "transactionId", None)
        original_transaction_id = getattr(decoded, "originalTransactionId", None)
        if not transaction_id or not original_transaction_id:
            raise StoreVerificationError("Apple transaction identifiers are missing")

        expires_ms = getattr(decoded, "expiresDate", None)
        if expires_ms is None:
            raise StoreVerificationError("Apple auto-renewable subscription expiry is missing")
        expires_at = datetime.fromtimestamp(expires_ms / 1000, tz=timezone.utc)
        revoked = (
            getattr(decoded, "revocationDate", None) is not None
            or getattr(decoded, "isUpgraded", False) is True
        )
        return VerifiedStorePurchase(
            provider=StoreProvider.APPLE,
            product_id=decoded.productId,
            application_id=decoded.bundleId,
            account_binding_id=str(account_token),
            transaction_id=str(transaction_id),
            original_transaction_id=str(original_transaction_id),
            expires_at=expires_at,
            revoked=revoked,
            environment=environment,
        )


class GooglePlayVerifier:
    """Verify Google Play subscriptions with the Android Publisher API.

    A Google service-account credential and a separate HMAC key for token
    identity are supplied by deployment. Raw purchase tokens are never used
    as the durable original transaction identifier.
    """

    ACTIVE_STATES = {
        "SUBSCRIPTION_STATE_ACTIVE",
        "SUBSCRIPTION_STATE_IN_GRACE_PERIOD",
        "SUBSCRIPTION_STATE_CANCELED",
    }

    def __init__(self, *, publisher_client, token_hash_key: str) -> None:
        if publisher_client is None or not token_hash_key:
            raise ValueError("Google Publisher client and token hash key are required")
        self._publisher = publisher_client
        self._token_key = token_hash_key.encode("utf-8")

    @classmethod
    def from_service_account_info(cls, *, service_account_info: dict,
                                  token_hash_key: str):
        """Build the official Android Publisher v3 client from secret-managed credentials."""
        if not isinstance(service_account_info, dict) or not service_account_info:
            raise ValueError("Google service-account information is required")
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise StoreVerificationUnavailable(
                "install Google API client and google-auth server dependencies"
            ) from exc
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/androidpublisher"],
        )
        client = build("androidpublisher", "v3", credentials=credentials,
                       cache_discovery=False)
        return cls(publisher_client=client, token_hash_key=token_hash_key)

    def _get_subscription(self, package_name: str, purchase_token: str) -> dict:
        try:
            result = self._publisher.purchases().subscriptionsv2().get(
                packageName=package_name, token=purchase_token
            ).execute()
        except Exception as exc:
            raise StoreVerificationError("Google Play subscription lookup failed") from exc
        if not isinstance(result, dict):
            raise StoreVerificationError("Google Play returned an invalid subscription response")
        return result

    def verify(self, request: StorePurchaseRequest) -> VerifiedStorePurchase:
        if request.provider is not StoreProvider.GOOGLE_PLAY:
            raise StoreVerificationError("Google Play verifier received a non-Google purchase")
        if not request.purchase_token or not request.purchase_token.strip():
            raise StoreVerificationError("Google Play purchase token is required")
        if not request.application_id or not request.application_id.strip():
            raise StoreVerificationError("Google Play package name is required")

        response = self._get_subscription(request.application_id, request.purchase_token)
        state = response.get("subscriptionState")
        external = response.get("externalAccountIdentifiers") or {}
        account_binding = external.get("obfuscatedExternalAccountId")
        if not account_binding or not hmac.compare_digest(
            str(account_binding), request.account_binding_id
        ):
            raise StoreVerificationError(
                "Google Play obfuscatedExternalAccountId does not match authenticated account"
            )
        line_items = response.get("lineItems") or []
        matching = [item for item in line_items
                    if item.get("productId") == request.product_id]
        if len(matching) != 1:
            raise StoreVerificationError("Google Play product does not match verified subscription")
        item = matching[0]
        expiry_value = item.get("expiryTime")
        if not expiry_value:
            raise StoreVerificationError("Google Play subscription expiry is missing")
        try:
            expiry = datetime.fromisoformat(expiry_value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise StoreVerificationError("Google Play subscription expiry is invalid") from exc
        if expiry.tzinfo is None:
            raise StoreVerificationError("Google Play subscription expiry has no timezone")
        if state not in self.ACTIVE_STATES:
            raise StoreVerificationError("Google Play subscription is not entitled")
        if expiry <= datetime.now(timezone.utc):
            raise StoreVerificationError("Google Play subscription has expired")

        acknowledgement = response.get("acknowledgementState")
        if acknowledgement == "ACKNOWLEDGEMENT_STATE_PENDING":
            try:
                self._publisher.purchases().subscriptions().acknowledge(
                    packageName=request.application_id,
                    subscriptionId=request.product_id,
                    token=request.purchase_token,
                    body={},
                ).execute()
            except Exception as exc:
                raise StoreVerificationError("Google Play purchase acknowledgement failed") from exc
            response = self._get_subscription(request.application_id, request.purchase_token)
            if response.get("acknowledgementState") != "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED":
                raise StoreVerificationError("Google Play purchase remains unacknowledged")

        order_id = item.get("latestSuccessfulOrderId") or response.get("latestOrderId")
        if not order_id:
            raise StoreVerificationError("Google Play order identifier is missing")
        token_digest = hmac.new(
            self._token_key, request.purchase_token.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return VerifiedStorePurchase(
            provider=StoreProvider.GOOGLE_PLAY,
            product_id=request.product_id,
            application_id=request.application_id,
            account_binding_id=str(account_binding),
            transaction_id=str(order_id),
            original_transaction_id=token_digest,
            expires_at=expiry,
            revoked=False,
            environment="production",
        )


class UnconfiguredStoreVerifier:
    def verify(self, request: StorePurchaseRequest) -> VerifiedStorePurchase:
        raise StoreVerificationUnavailable(
            request.provider.value + " live verification is not configured"
        )


@dataclass(frozen=True)
class StoreProduct:
    provider: StoreProvider
    product_id: str
    application_id: str
    package: Package

    def __post_init__(self) -> None:
        if not self.product_id.strip() or not self.application_id.strip():
            raise ValueError("store product and application identifiers are required")


class StoreVerificationService:
    """Map store-verified purchase facts to server-authoritative entitlements."""

    def __init__(
        self,
        *,
        apple_verifier: StoreVerifier | None = None,
        google_verifier: StoreVerifier | None = None,
        products: Iterable[StoreProduct] = (),
    ) -> None:
        self._verifiers = {
            StoreProvider.APPLE: apple_verifier or UnconfiguredStoreVerifier(),
            StoreProvider.GOOGLE_PLAY: google_verifier or UnconfiguredStoreVerifier(),
        }
        product_list = tuple(products)
        self._products = {(p.provider, p.product_id): p for p in product_list}
        if len(self._products) != len(product_list):
            raise ValueError("duplicate store product mapping")

    def _verify_purchase(
        self,
        request: StorePurchaseRequest,
        *,
        expected_account_binding_id: str,
        reject_revoked: bool,
    ) -> tuple[VerifiedStorePurchase, Package]:
        """Verify provider evidence and enforce the server-owned product catalogue."""
        if not isinstance(request.provider, StoreProvider):
            raise StoreVerificationError("unsupported store provider")
        if not request.purchase_token or not request.purchase_token.strip():
            raise StoreVerificationError("purchase evidence is required")
        if (
            not expected_account_binding_id
            or request.account_binding_id != expected_account_binding_id
        ):
            raise StoreVerificationError("authenticated account binding mismatch")
        product = self._products.get((request.provider, request.product_id))
        if product is None:
            raise StoreVerificationError("unknown store product")
        if request.application_id != product.application_id:
            raise StoreVerificationError("application identifier mismatch")

        verified = self._verifiers[request.provider].verify(request)
        if verified.provider is not request.provider:
            raise StoreVerificationError("provider mismatch")
        if verified.product_id != product.product_id or verified.application_id != product.application_id:
            raise StoreVerificationError("verified product or application mismatch")
        if verified.account_binding_id != expected_account_binding_id:
            raise StoreVerificationError("verified account binding mismatch")
        if reject_revoked and verified.revoked:
            raise StoreVerificationError("purchase was refunded or revoked")
        return verified, product.package

    def verify_purchase(
        self,
        request: StorePurchaseRequest,
        *,
        expected_account_binding_id: str,
    ) -> tuple[VerifiedStorePurchase, Package]:
        """Return provider-verified active purchase facts and package mapping."""
        return self._verify_purchase(
            request,
            expected_account_binding_id=expected_account_binding_id,
            reject_revoked=True,
        )

    def verify(
        self,
        request: StorePurchaseRequest,
        *,
        expected_account_binding_id: str,
        now: datetime | None = None,
    ) -> SubscriptionSnapshot:
        verified, package = self.verify_purchase(
            request, expected_account_binding_id=expected_account_binding_id
        )
        current = now or datetime.now(timezone.utc)
        active = not verified.revoked and (verified.expires_at is None or current < verified.expires_at)
        return SubscriptionSnapshot(package, active=active, expires_at=verified.expires_at)

    def verify_and_persist(
        self,
        request: StorePurchaseRequest,
        *,
        subject_id: str,
        expected_account_binding_id: str,
        repository,
        now: datetime | None = None,
    ) -> SubscriptionSnapshot:
        """Verify with the provider first, persist facts second, then return the entitlement."""
        verified, package = self._verify_purchase(
            request,
            expected_account_binding_id=expected_account_binding_id,
            reject_revoked=False,
        )
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        repository.save_verified_purchase(
            subject_id=subject_id,
            request=request,
            purchase=verified,
            package=package,
            verified_at=current,
        )
        active = not verified.revoked and (
            verified.expires_at is None or current < verified.expires_at
        )
        return SubscriptionSnapshot(package, active=active, expires_at=verified.expires_at)
