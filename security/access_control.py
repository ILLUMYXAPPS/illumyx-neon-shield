"""Local-first access-control primitives for Neon Shield.

This module intentionally does not provide remote ownership changes. Ownership
state can only be initialized explicitly and security-sensitive mutations
require the existing owner identity to be presented for every operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import hmac
import secrets


class AccessRole(str, Enum):
    OWNER = "owner"
    TRUSTED_DEVICE = "trusted_device"
    READ_ONLY = "read_only"


@dataclass(frozen=True)
class AuditEvent:
    action: str
    actor: AccessRole
    timestamp: str
    success: bool


@dataclass
class AccessControl:
    """Small deterministic policy engine suitable for local integration tests."""

    owner_token_hash: str | None = None
    trusted_device_ids: set[str] = field(default_factory=set)
    audit_log: list[AuditEvent] = field(default_factory=list)

    @staticmethod
    def hash_owner_token(token: str, salt: bytes) -> str:
        if not token:
            raise ValueError("owner token must not be empty")
        return sha256(salt + token.encode("utf-8")).hexdigest()

    def initialize_owner(self, token: str, salt: bytes) -> None:
        """Initialize ownership once. Re-initialization is always rejected."""
        if self.owner_token_hash is not None:
            self._audit("owner_reinitialization", AccessRole.OWNER, False)
            raise PermissionError("ownership is already initialized")
        self.owner_token_hash = self.hash_owner_token(token, salt)
        self._audit("owner_initialized", AccessRole.OWNER, True)

    def verify_owner(self, token: str, salt: bytes) -> bool:
        if self.owner_token_hash is None:
            return False
        candidate = self.hash_owner_token(token, salt)
        return hmac.compare_digest(candidate, self.owner_token_hash)

    def add_trusted_device(self, actor_token: str, salt: bytes, device_id: str) -> None:
        """Only the current owner can add a trusted device."""
        if not device_id:
            raise ValueError("device_id must not be empty")
        if not self.verify_owner(actor_token, salt):
            self._audit("trusted_device_add", AccessRole.TRUSTED_DEVICE, False)
            raise PermissionError("owner verification required")
        self.trusted_device_ids.add(device_id)
        self._audit("trusted_device_add", AccessRole.OWNER, True)

    def remove_trusted_device(self, actor_token: str, salt: bytes, device_id: str) -> None:
        """Only the current owner can remove a trusted device."""
        if not self.verify_owner(actor_token, salt):
            self._audit("trusted_device_remove", AccessRole.TRUSTED_DEVICE, False)
            raise PermissionError("owner verification required")
        self.trusted_device_ids.discard(device_id)
        self._audit("trusted_device_remove", AccessRole.OWNER, True)

    def is_trusted(self, device_id: str) -> bool:
        return device_id in self.trusted_device_ids

    def _audit(self, action: str, actor: AccessRole, success: bool) -> None:
        self.audit_log.append(
            AuditEvent(
                action=action,
                actor=actor,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=success,
            )
        )


def generate_owner_secret() -> str:
    """Generate a high-entropy bootstrap secret; never log or hard-code it."""
    return secrets.token_urlsafe(32)
