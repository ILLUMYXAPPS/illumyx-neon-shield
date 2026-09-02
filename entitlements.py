"""Server-authoritative package entitlement policy for Neon Shield.

This module deliberately models entitlement decisions only. It does not process
payments or trust client-supplied package state. A production subscription
adapter must construct the immutable SubscriptionSnapshot from verified billing
and account data before calling EntitlementPolicy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class Package(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    PREMIUM_FAMILY = "premium_family"


class Feature(str, Enum):
    CORE_SECURITY = "core_security"
    TRUSTED_DEVICE_MANAGEMENT = "trusted_device_management"
    ADVANCED_UNKNOWN_DEVICE_PROTECTION = "advanced_unknown_device_protection"
    SECURITY_ALERTS = "security_alerts"
    SECURITY_AUDIT_HISTORY = "security_audit_history"
    ADVANCED_ACCOUNT_PROTECTION = "advanced_account_protection"
    ENHANCED_DEVICE_LOGIN_CONTROLS = "enhanced_device_login_controls"
    MULTI_DEVICE_PROTECTION = "multi_device_protection"
    FAMILY_PROTECTION = "family_protection"


@dataclass(frozen=True)
class SubscriptionSnapshot:
    """Verified server-side subscription state used for entitlement decisions."""

    package: Package
    active: bool
    expires_at: datetime | None = None
    family_member_count: int = 0

    def __post_init__(self) -> None:
        if self.family_member_count < 0:
            raise ValueError("family_member_count must not be negative")
        if self.family_member_count > EntitlementPolicy.MAX_FAMILY_MEMBERS:
            raise ValueError("family_member_count must not exceed five")
        if self.package is not Package.PREMIUM_FAMILY and self.family_member_count:
            raise ValueError("family members require Premium Family")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")

    def is_current(self, now: datetime | None = None) -> bool:
        if not self.active:
            return False
        if self.expires_at is None:
            return True
        current = now or datetime.now(timezone.utc)
        return current < self.expires_at


class IdentityServiceLike(Protocol):
    """Minimal auth boundary required before a protected feature is authorized."""

    def resolve_session(self, session_id: str):
        """Resolve an active server-authoritative session."""
        ...


class EntitlementPolicy:
    """Fail-closed feature policy evaluated from trusted subscription state."""

    _FREE_FEATURES = frozenset({Feature.CORE_SECURITY})
    _PREMIUM_FEATURES = frozenset(
        {
            Feature.TRUSTED_DEVICE_MANAGEMENT,
            Feature.ADVANCED_UNKNOWN_DEVICE_PROTECTION,
            Feature.SECURITY_ALERTS,
            Feature.SECURITY_AUDIT_HISTORY,
            Feature.ADVANCED_ACCOUNT_PROTECTION,
            Feature.ENHANCED_DEVICE_LOGIN_CONTROLS,
            Feature.MULTI_DEVICE_PROTECTION,
        }
    )
    _FAMILY_FEATURES = frozenset({Feature.FAMILY_PROTECTION})
    MAX_FAMILY_MEMBERS = 5

    @classmethod
    def allows(
        cls,
        snapshot: SubscriptionSnapshot,
        feature: Feature,
        *,
        now: datetime | None = None,
    ) -> bool:
        if not snapshot.is_current(now):
            return False
        if feature in cls._FREE_FEATURES:
            return True
        if snapshot.package is Package.FREE:
            return False
        if feature in cls._PREMIUM_FEATURES:
            return True
        if feature in cls._FAMILY_FEATURES:
            return snapshot.package is Package.PREMIUM_FAMILY
        return False

    @classmethod
    def authorize_feature(
        cls,
        identity_service: IdentityServiceLike,
        session_id: str,
        snapshot: SubscriptionSnapshot,
        feature: Feature,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Require an active server session before applying package entitlement."""
        identity_service.resolve_session(session_id)
        return cls.allows(snapshot, feature, now=now)

    @classmethod
    def family_member_allowed(
        cls,
        snapshot: SubscriptionSnapshot,
        *,
        member_number: int,
        now: datetime | None = None,
    ) -> bool:
        if snapshot.package is not Package.PREMIUM_FAMILY:
            return False
        if not snapshot.is_current(now):
            return False
        if not 1 <= member_number <= cls.MAX_FAMILY_MEMBERS:
            return False
        return member_number <= snapshot.family_member_count
