"""Persistent server-authoritative authentication implementation."""
from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta, timezone

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, IdentityService, ServerSession, SignInRequest
from backend.store import AuthStore, verify_secret


class PersistentIdentityService(IdentityService):
    """Hashed credentials, opaque rotating sessions and persistent device policy."""

    def __init__(self, store: AuthStore, session_ttl: timedelta = timedelta(minutes=15), max_sign_ins: int = 5) -> None:
        if session_ttl <= timedelta(0) or max_sign_ins < 1:
            raise ValueError("invalid authentication limits")
        self.store = store
        self.session_ttl = session_ttl
        self.max_sign_ins = max_sign_ins
        self._failed_attempts: dict[str, tuple[int, float]] = {}

    def _rate_limited(self, identity: str) -> bool:
        count, started = self._failed_attempts.get(identity, (0, time.monotonic()))
        if time.monotonic() - started >= 300:
            self._failed_attempts.pop(identity, None)
            return False
        return count >= self.max_sign_ins

    def _failure(self, identity: str) -> None:
        count, started = self._failed_attempts.get(identity, (0, time.monotonic()))
        self._failed_attempts[identity] = (count + 1, started)

    def sign_in(self, request: SignInRequest) -> ServerSession:
        identity = request.identity.strip().lower()
        if not identity or not request.credential or not request.device_id:
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        if self._rate_limited(identity):
            raise AuthenticationError(AuthFailure.RATE_LIMITED)
        user = self.store.find_user(identity)
        if user is None or not verify_secret(request.credential, user["credential_record"]):
            self._failure(identity)
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        subject_id = user["subject_id"]
        if self.store.identity_blocked(subject_id):
            self.store.add_audit("blocked_identity", subject_id, request.device_id)
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)
        if request.phone_identity and self.store.phone_blocked(request.phone_identity):
            self.store.add_audit("blocked_phone", subject_id, request.device_id)
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)
        if not self.store.device_trusted(subject_id, request.device_id):
            self.store.add_audit("untrusted_device", subject_id, request.device_id)
            raise AuthenticationError(AuthFailure.UNTRUSTED_DEVICE)
        now = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        session = ServerSession(token, subject_id, request.device_id, now, now + self.session_ttl)
        self.store.save_session(token, subject_id, request.device_id, now.isoformat(), session.expires_at.isoformat())
        self.store.add_audit("session_issued", subject_id, request.device_id)
        self._failed_attempts.pop(identity, None)
        return session

    def _load_row(self, token: str):
        row = self.store.get_session(token)
        if row is None or row["revoked"]:
            raise AuthenticationError(AuthFailure.REVOKED_SESSION if row and row["revoked"] else AuthFailure.EXPIRED_SESSION)
        if datetime.now(timezone.utc) >= datetime.fromisoformat(row["expires_at"]):
            self.store.revoke_session(token)
            self.store.add_audit_fingerprint("expired_session", row["subject_id"], row["device_hash"])
            raise AuthenticationError(AuthFailure.EXPIRED_SESSION)
        if self.store.identity_blocked(row["subject_id"]):
            self.store.add_audit_fingerprint("blocked_identity_session", row["subject_id"], row["device_hash"])
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)
        if not self.store.device_hash_trusted(row["subject_id"], row["device_hash"]):
            self.store.add_audit_fingerprint("untrusted_device_session", row["subject_id"], row["device_hash"])
            raise AuthenticationError(AuthFailure.UNTRUSTED_DEVICE)
        return row

    def refresh_token(self, token: str) -> ServerSession:
        row = self._load_row(token)
        now = datetime.now(timezone.utc)
        new_token = secrets.token_urlsafe(32)
        self.store.revoke_session(token)
        self.store.save_session_hash(new_token, row["subject_id"], row["device_hash"], now.isoformat(), (now + self.session_ttl).isoformat())
        self.store.add_audit_fingerprint("session_refreshed", row["subject_id"], row["device_hash"])
        return ServerSession(new_token, row["subject_id"], row["device_hash"], now, now + self.session_ttl)

    def revoke_token(self, token: str) -> None:
        row = self._load_row(token)
        self.store.revoke_session(token)
        self.store.add_audit_fingerprint("session_revoked", row["subject_id"], row["device_hash"])

    def refresh(self, session: ServerSession) -> ServerSession:
        return self.refresh_token(session.session_id)

    def revoke(self, session: ServerSession) -> None:
        self.revoke_token(session.session_id)

    def is_device_trusted(self, session: ServerSession) -> bool:
        return self.store.device_hash_trusted(session.subject_id, session.device_id) if len(session.device_id) == 64 else self.store.device_trusted(session.subject_id, session.device_id)

    def is_identity_blocked(self, subject_id: str) -> bool:
        return self.store.identity_blocked(subject_id)
