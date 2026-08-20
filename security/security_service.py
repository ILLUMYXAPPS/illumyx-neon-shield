"""Application-facing security service for Neon Shield.

UI code should depend on this service rather than mutating AccessControl directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .access_control import AccessControl, AuditEvent


@dataclass(frozen=True)
class SecuritySnapshot:
    owner_initialized: bool
    trusted_device_count: int
    audit_event_count: int


class SecurityService:
    """Thin application boundary around the local access-control policy."""

    def __init__(self, access_control: AccessControl | None = None) -> None:
        self._access_control = access_control or AccessControl()

    @property
    def access_control(self) -> AccessControl:
        """Expose the policy only to trusted application-layer code."""
        return self._access_control

    def snapshot(self) -> SecuritySnapshot:
        return SecuritySnapshot(
            owner_initialized=self._access_control.owner_token_hash is not None,
            trusted_device_count=len(self._access_control.trusted_device_ids),
            audit_event_count=len(self._access_control.audit_log),
        )

    def initialize_owner(self, token: str, salt: bytes) -> None:
        self._access_control.initialize_owner(token, salt)

    def verify_owner(self, token: str, salt: bytes) -> bool:
        return self._access_control.verify_owner(token, salt)

    def add_trusted_device(self, owner_token: str, salt: bytes, device_id: str) -> None:
        self._access_control.add_trusted_device(owner_token, salt, device_id)

    def remove_trusted_device(self, owner_token: str, salt: bytes, device_id: str) -> None:
        self._access_control.remove_trusted_device(owner_token, salt, device_id)

    def is_trusted_device(self, device_id: str) -> bool:
        return self._access_control.is_trusted(device_id)

    def audit_events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._access_control.audit_log)
