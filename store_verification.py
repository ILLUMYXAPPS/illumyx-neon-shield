"""Fail-closed boundary for direct Apple App Store and Google Play verification."""
from __future__ import annotations

from dataclasses import dataclass
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
