"""Safe, dependency-free authentication service implementation for Neon Shield.

This is an in-process reference implementation for tests and integration work.
It deliberately does not expose HTTP endpoints, persist credentials, or hold
production secrets. A production adapter must provide those concerns through
managed infrastructure while preserving the auth_server_contract boundary.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable

from auth_server_contract import (
    AuthFailure,
    IdentityService,
    ServerSession,
    SignInRequest,
)


class AuthenticationError(Exception):
    """Structured authentication failure safe for mapping to an API response."""

    def __init__(self, failure: AuthFailure) -> None:
        super().__init__(failure.value)
        self.failure = failure


@dataclass(frozen=True)
class SecurityAuditEvent:
    """Hash-chained security event without credentials or raw device identifiers."""

    event_type: str
    occurred_at: datetime
    device_fingerprint: str
    previous_hash: str
    event_hash: str


class InMemoryIdentityService(IdentityService):
    """Reference implementation with injected credential verification."""

    def __init__(
        self,
        verify_credential: Callable[[str, str], str | None],
        trusted_devices: Iterable[str] = (),
        blocked_subjects: Iterable[str] = (),
        blocked_phones: Iterable[str] = (),
        session_ttl: timedelta = timedelta(minutes=15),
        max_sign_ins: int = 5,
    ) -> None:
        if session_ttl <= timedelta(0):
            raise ValueError("session_ttl must be positive")
        if max_sign_ins < 1:
            raise ValueError("max_sign_ins must be positive")

        self._verify_credential = verify_credential
        self._trusted_devices = set(trusted_devices)
        self._blocked_subjects = set(blocked_subjects)
        self._blocked_phones = set(blocked_phones)
        self._session_ttl = session_ttl
        self._max_sign_ins = max_sign_ins
        self._sign_in_counts: dict[str, int] = {}
        self._sessions: dict[str, ServerSession] = {}
        self._revoked: set[str] = set()
        self._audit_events: list[SecurityAuditEvent] = []

    def sign_in(self, request: SignInRequest) -> ServerSession:
        if not request.identity or not request.device_id:
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)

        attempts = self._sign_in_counts.get(request.identity, 0)
        if attempts >= self._max_sign_ins:
            raise AuthenticationError(AuthFailure.RATE_LIMITED)
        self._sign_in_counts[request.identity] = attempts + 1

        subject_id = self._verify_credential(request.identity, request.credential)
        if subject_id is None:
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        if self.is_identity_blocked(subject_id):
            self._record_audit("blocked_identity", request.device_id)
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)
        if request.phone_identity is not None and request.phone_identity in self._blocked_phones:
            self._record_audit("blocked_phone", request.device_id)
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)
        if not self._is_device_id_trusted(request.device_id):
            self._record_audit("untrusted_device", request.device_id)
            raise AuthenticationError(AuthFailure.UNTRUSTED_DEVICE)

        now = datetime.now(timezone.utc)
        session = ServerSession(
            session_id=secrets.token_urlsafe(32),
            subject_id=subject_id,
            device_id=request.device_id,
            issued_at=now,
            expires_at=now + self._session_ttl,
        )
        self._sessions[session.session_id] = session
        self._record_audit("session_issued", request.device_id)
        return session

    def resolve_session(self, session_id: str) -> ServerSession:
        if not session_id:
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        session = self._sessions.get(session_id)
        if session is None:
            if session_id in self._revoked:
                raise AuthenticationError(AuthFailure.REVOKED_SESSION)
            raise AuthenticationError(AuthFailure.EXPIRED_SESSION)
        self._require_active(session)
        return session

    def refresh(self, session: ServerSession) -> ServerSession:
        self._require_active(session)
        if not self.is_device_trusted(session):
            self._record_audit("untrusted_device_refresh", session.device_id)
            raise AuthenticationError(AuthFailure.UNTRUSTED_DEVICE)

        now = datetime.now(timezone.utc)
        refreshed = ServerSession(
            session_id=secrets.token_urlsafe(32),
            subject_id=session.subject_id,
            device_id=session.device_id,
            issued_at=now,
            expires_at=now + self._session_ttl,
        )
        self._revoked.add(session.session_id)
        self._sessions.pop(session.session_id, None)
        self._sessions[refreshed.session_id] = refreshed
        self._record_audit("session_refreshed", session.device_id)
        return refreshed

    def revoke(self, session: ServerSession) -> None:
        self._revoked.add(session.session_id)
        self._sessions.pop(session.session_id, None)
        self._record_audit("session_revoked", session.device_id)

    def is_device_trusted(self, session: ServerSession) -> bool:
        return self._is_device_id_trusted(session.device_id)

    def is_identity_blocked(self, subject_id: str) -> bool:
        return subject_id in self._blocked_subjects

    def audit_events(self) -> tuple[SecurityAuditEvent, ...]:
        return tuple(self._audit_events)

    def _is_device_id_trusted(self, device_id: str) -> bool:
        return device_id in self._trusted_devices

    def _require_active(self, session: ServerSession) -> None:
        if session.session_id in self._revoked:
            raise AuthenticationError(AuthFailure.REVOKED_SESSION)
        if session.session_id not in self._sessions:
            raise AuthenticationError(AuthFailure.EXPIRED_SESSION)
        if datetime.now(timezone.utc) >= session.expires_at:
            self._revoked.add(session.session_id)
            self._sessions.pop(session.session_id, None)
            self._record_audit("expired_session", session.device_id)
            raise AuthenticationError(AuthFailure.EXPIRED_SESSION)
        if self.is_identity_blocked(session.subject_id):
            self._record_audit("blocked_identity_session", session.device_id)
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)
        if not self.is_device_trusted(session):
            self._record_audit("untrusted_device_session", session.device_id)
            raise AuthenticationError(AuthFailure.UNTRUSTED_DEVICE)

    def _record_audit(self, event_type: str, device_id: str) -> None:
        occurred_at = datetime.now(timezone.utc)
        fingerprint = hashlib.sha256(device_id.encode("utf-8")).hexdigest()
        previous_hash = self._audit_events[-1].event_hash if self._audit_events else "0" * 64
        payload = {
            "event_type": event_type,
            "occurred_at": occurred_at.isoformat(),
            "device_fingerprint": fingerprint,
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self._audit_events.append(
            SecurityAuditEvent(
                event_type=event_type,
                occurred_at=occurred_at,
                device_fingerprint=fingerprint,
                previous_hash=previous_hash,
                event_hash=event_hash,
            )
        )
