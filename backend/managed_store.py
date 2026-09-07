"""Production persistence boundary for Neon Shield.

This module deliberately defines the interface only. The local SQLite AuthStore
remains the development/integration adapter. Production deployments must supply
a managed durable implementation behind this boundary.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ManagedAuthStore(ABC):
    """Durable production storage contract for server-authoritative auth."""

    @abstractmethod
    def create_user(self, subject_id: str, identity: str, credential: str) -> None: ...

    @abstractmethod
    def trust_device(self, subject_id: str, device_id: str) -> None: ...

    @abstractmethod
    def set_device_trusted(self, subject_id: str, device_id: str, trusted: bool) -> None: ...

    @abstractmethod
    def block_phone(self, phone: str) -> None: ...

    @abstractmethod
    def find_user(self, identity: str) -> Any: ...

    @abstractmethod
    def device_trusted(self, subject_id: str, device_id: str) -> bool: ...

    @abstractmethod
    def device_hash_trusted(self, subject_id: str, device_hash: str) -> bool: ...

    @abstractmethod
    def identity_blocked(self, subject_id: str) -> bool: ...

    @abstractmethod
    def phone_blocked(self, phone: str) -> bool: ...

    @abstractmethod
    def save_session(self, token: str, subject_id: str, device_id: str, issued_at: str, expires_at: str) -> None: ...

    @abstractmethod
    def save_session_hash(self, token: str, subject_id: str, device_hash: str, issued_at: str, expires_at: str) -> None: ...

    @abstractmethod
    def get_session(self, token: str) -> Any: ...

    @abstractmethod
    def revoke_session(self, token: str) -> None: ...

    @abstractmethod
    def last_audit_hash(self) -> str: ...

    @abstractmethod
    def add_audit(self, event_type: str, subject_id: str | None, device_id: str) -> str: ...

    @abstractmethod
    def add_audit_fingerprint(self, event_type: str, subject_id: str | None, device_fingerprint: str) -> str: ...

    def close(self) -> None:
        return None
