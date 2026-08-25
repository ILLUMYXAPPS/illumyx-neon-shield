"""Neon Shield server-authoritative authentication boundary.

Local/staging reference implementation. Production deployment must use HTTPS,
a managed database, secret management, rate limiting, monitoring, and an
independent identity-verification provider before release.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

TOKEN_BYTES = 32
PASSWORD_ITERATIONS = 600_000
SESSION_TTL_SECONDS = 3600


class AuthError(Exception):
    """Raised when authentication or device policy denies an operation."""


@dataclass(frozen=True)
class Session:
    token: str
    user_id: str
    device_id: str
    expires_at: int


class AuthStore:
    """SQLite-backed authentication store for local/staging use."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(database)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                blocked INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS trusted_devices (
                user_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                PRIMARY KEY (user_id, device_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash BLOB PRIMARY KEY,
                user_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """
        )
        self.connection.commit()

    @staticmethod
    def _password_hash(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
        )

    @staticmethod
    def _token_hash(token: str) -> bytes:
        return hashlib.sha256(token.encode("ascii")).digest()

    def create_user(self, email: str, password: str) -> str:
        if len(password) < 12:
            raise AuthError("password must be at least 12 characters")
        user_id = secrets.token_urlsafe(16)
        salt = secrets.token_bytes(16)
        password_hash = self._password_hash(password, salt)
        try:
            self.connection.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, 0)",
                (user_id, email.strip().lower(), salt, password_hash),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise AuthError("identity already exists") from exc
        return user_id

    def enroll_device(self, user_id: str, device_id: str) -> None:
        device_id = device_id.strip()
        if not device_id:
            raise AuthError("device identity is required")
        if not self._user_exists(user_id):
            raise AuthError("identity not found")
        self.connection.execute(
            "INSERT OR IGNORE INTO trusted_devices VALUES (?, ?)",
            (user_id, device_id),
        )
        self.connection.commit()

    def revoke_device(self, user_id: str, device_id: str) -> None:
        self.connection.execute(
            "DELETE FROM trusted_devices WHERE user_id = ? AND device_id = ?",
            (user_id, device_id.strip()),
        )
        self.connection.execute(
            "UPDATE sessions SET revoked = 1 WHERE user_id = ? AND device_id = ?",
            (user_id, device_id.strip()),
        )
        self.connection.commit()

    def set_blocked(self, user_id: str, blocked: bool = True) -> None:
        self.connection.execute(
            "UPDATE users SET blocked = ? WHERE user_id = ?", (int(blocked), user_id)
        )
        if blocked:
            self.connection.execute(
                "UPDATE sessions SET revoked = 1 WHERE user_id = ?", (user_id,)
            )
        self.connection.commit()

    def authenticate(self, email: str, password: str, device_id: str) -> Session:
        row = self.connection.execute(
            "SELECT user_id, password_salt, password_hash, blocked FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
        if row is None:
            raise AuthError("authentication denied")
        user_id, salt, expected_hash, blocked = row
        candidate = self._password_hash(password, salt)
        if blocked or not hmac.compare_digest(candidate, expected_hash):
            self._event(user_id, device_id, "login_denied", "invalid identity or blocked account")
            raise AuthError("authentication denied")
        trusted = self.connection.execute(
            "SELECT 1 FROM trusted_devices WHERE user_id = ? AND device_id = ?",
            (user_id, device_id.strip()),
        ).fetchone()
        if trusted is None:
            self._event(user_id, device_id, "unsupported_login", "unrecognised device")
            raise AuthError("device is not trusted")

        token = secrets.token_urlsafe(TOKEN_BYTES)
        expires_at = int(time.time()) + SESSION_TTL_SECONDS
        self.connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, 0)",
            (self._token_hash(token), user_id, device_id.strip(), expires_at),
        )
        self._event(user_id, device_id, "session_issued", "trusted device authenticated")
        self.connection.commit()
        return Session(token, user_id, device_id.strip(), expires_at)

    def validate_session(self, token: str) -> Session:
        row = self.connection.execute(
            "SELECT user_id, device_id, expires_at, revoked FROM sessions WHERE token_hash = ?",
            (self._token_hash(token),),
        ).fetchone()
        if row is None:
            raise AuthError("session denied")
        user_id, device_id, expires_at, revoked = row
        if revoked or expires_at <= int(time.time()):
            raise AuthError("session denied")
        trusted = self.connection.execute(
            "SELECT 1 FROM trusted_devices WHERE user_id = ? AND device_id = ?",
            (user_id, device_id),
        ).fetchone()
        if trusted is None:
            raise AuthError("session denied")
        return Session(token, user_id, device_id, expires_at)

    def revoke_session(self, token: str) -> None:
        self.connection.execute(
            "UPDATE sessions SET revoked = 1 WHERE token_hash = ?",
            (self._token_hash(token),),
        )
        self.connection.commit()

    def _user_exists(self, user_id: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
        ).fetchone() is not None

    def _event(self, user_id: str | None, device_id: str, event_type: str, reason: str) -> None:
        self.connection.execute(
            "INSERT INTO security_events(user_id, device_id, event_type, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, device_id.strip(), event_type, reason, int(time.time())),
        )


if __name__ == "__main__":
    print("Neon Shield auth boundary module. Integrate behind HTTPS before deployment.")
