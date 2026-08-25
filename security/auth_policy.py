"""Central authentication policy for Neon Shield.

This module is deliberately framework-neutral so the eventual authentication
backend can call one policy rather than duplicating trusted-device rules.
"""

from dataclasses import dataclass
from enum import Enum


class AuthorizationDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class AuthorizationRequest:
    owner_initialized: bool
    device_id: str
    trusted_device_ids: frozenset[str]
    normalized_phone: str
    blocked_phone: bool = False


@dataclass(frozen=True)
class AuthorizationResult:
    decision: AuthorizationDecision
    reason: str

    @property
    def allowed(self) -> bool:
        return self.decision is AuthorizationDecision.ALLOW


def authorize(request: AuthorizationRequest) -> AuthorizationResult:
    """Apply Neon Shield's authentication policy before session issuance."""
    device_id = request.device_id.strip()
    phone = request.normalized_phone.strip()

    if not request.owner_initialized:
        return AuthorizationResult(AuthorizationDecision.DENY, "owner_not_initialized")
    if not device_id:
        return AuthorizationResult(AuthorizationDecision.DENY, "device_identity_missing")
    if device_id not in request.trusted_device_ids:
        return AuthorizationResult(AuthorizationDecision.DENY, "unrecognised_device")
    if not phone:
        return AuthorizationResult(AuthorizationDecision.DENY, "phone_identity_missing")
    if request.blocked_phone:
        return AuthorizationResult(AuthorizationDecision.DENY, "blocked_phone")

    return AuthorizationResult(AuthorizationDecision.ALLOW, "trusted_device_and_valid_identity")
