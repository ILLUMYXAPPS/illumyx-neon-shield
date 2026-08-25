"""Provider-neutral server-side authentication contract for Neon Shield.

This module defines the domain boundary only. It intentionally does not
implement password verification, token signing, persistence, or networking.
Those responsibilities belong to the production identity service and must be
backed by managed infrastructure and secrets outside source control.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol


class AuthFailure(str, Enum):
    INVALID_CREDENTIALS = "invalid_credentials"
    EXPIRED_SESSION = "expired_session"
    REVOKED_SESSION = "revoked_session"
    UNTRUSTED_DEVICE = "untrusted_device"
    BLOCKED_IDENTITY = "blocked_identity"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ServerSession:
    session_id: str
    subject_id: str
    device_id: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class SignInRequest:
    identity: str
    credential: str
    device_id: str


class IdentityService(Protocol):
    """Interface implemented by the eventual production identity provider."""

    def sign_in(self, request: SignInRequest) -> ServerSession:
        """Authenticate identity and issue a short-lived server session."""
        ...

    def refresh(self, session: ServerSession) -> ServerSession:
        """Rotate/refresh a valid server session."""
        ...

    def revoke(self, session: ServerSession) -> None:
        """Revoke the server-side session."""
        ...

    def is_device_trusted(self, session: ServerSession) -> bool:
        """Ask the authoritative service whether the device is trusted."""
        ...

    def is_identity_blocked(self, subject_id: str) -> bool:
        """Ask the authoritative service whether the identity is blocked."""
        ...
