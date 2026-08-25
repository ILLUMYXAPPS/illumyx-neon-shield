"""Safe, dependency-free authentication service implementation for Neon Shield.

This is an in-process reference implementation for tests and integration work.
It deliberately does not expose HTTP endpoints, persist credentials, or hold
production secrets. A production adapter must provide those concerns through
managed infrastructure while preserving the auth_server_contract boundary.
"""

from __future__ import annotations

import secrets
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


class InMemoryIdentityService(IdentityService):
    """Reference implementation with injected credential verification.

    Credentials are never stored or logged. The verifier receives the supplied
    identity and credential and returns the canonical subject ID on success.
    """

    def __init__(
        self,
        verify_credential: Callable[[str, str], str | None],
        trusted_devices: Iterable[str] = (),
        blocked_subjects: Iterable[str] = (),
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
        self._session_ttl = session_ttl
        self._max_sign_ins = max_sign_ins
        self._sign_in_counts: dict[str, int] = {}
        self._sessions: dict[str, ServerSession] = {}
        self._revoked: set[str] = set()

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
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)

        now = datetime.now(timezone.utc)
        session = ServerSession(
            session_id=secrets.token_urlsafe(32),
            subject_id=subject_id,
            device_id=request.device_id,
            issued_at=now,
            expires_at=now + self._session_ttl,
        )
        self._sessions[session.session_id] = session
        return session

    def refresh(self, session: ServerSession) -> ServerSession:
        self._require_active(session)
        if not self.is_device_trusted(session):
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
        return refreshed

    def revoke(self, session: ServerSession) -> None:
        self._revoked.add(session.session_id)
        self._sessions.pop(session.session_id, None)

    def is_device_trusted(self, session: ServerSession) -> bool:
        return session.device_id in self._trusted_devices

    def is_identity_blocked(self, subject_id: str) -> bool:
        return subject_id in self._blocked_subjects

    def _require_active(self, session: ServerSession) -> None:
        if session.session_id in self._revoked:
            raise AuthenticationError(AuthFailure.REVOKED_SESSION)
        if session.session_id not in self._sessions:
            raise AuthenticationError(AuthFailure.EXPIRED_SESSION)
        if datetime.now(timezone.utc) >= session.expires_at:
            self._revoked.add(session.session_id)
            self._sessions.pop(session.session_id, None)
            raise AuthenticationError(AuthFailure.EXPIRED_SESSION)
        if self.is_identity_blocked(session.subject_id):
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)
