"""Fail-closed boundary for direct Apple App Store and Google Play verification."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

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

    def __post_init__(self):
        if not self.transaction_id or not self.original_transaction_id:
            raise ValueError("transaction identifiers are required")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expiry must be timezone-aware")

class StoreVerifier(Protocol):
    def verify(self, request: StorePurchaseRequest) -> VerifiedStorePurchase: ...

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

class StoreVerificationService:
    """Map store-verified purchase facts to server-authoritative entitlements."""
    def __init__(self, *, apple_verifier=None, google_verifier=None, products=()):
        self._verifiers = {
            StoreProvider.APPLE: apple_verifier or UnconfiguredStoreVerifier(),
            StoreProvider.GOOGLE_PLAY: google_verifier or UnconfiguredStoreVerifier(),
        }
        self._products = {(p.provider, p.product_id): p for p in products}
        if len(self._products) != len(tuple(products)):
            raise ValueError("duplicate store product mapping")

    def verify(self, request: StorePurchaseRequest, *, expected_account_binding_id: str, now=None) -> SubscriptionSnapshot:
        if not request.purchase_token.strip():
            raise StoreVerificationError("purchase evidence is required")
        if not expected_account_binding_id or request.account_binding_id != expected_account_binding_id:
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
        if verified.revoked:
            raise StoreVerificationError("purchase was refunded or revoked")
        if verified.environment.lower() not in {"production", "sandbox"}:
            raise StoreVerificationError("unknown store environment")
        current = now or datetime.now(timezone.utc)
        active = verified.expires_at is None or current < verified.expires_at
        return SubscriptionSnapshot(product.package, active=active, expires_at=verified.expires_at)
