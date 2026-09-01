"""Persistent, privacy-safe storage for the Neon Shield auth boundary."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: str, pepper: str = "") -> str:
    return hashlib.sha256((pepper + value).encode("utf-8")).hexdigest()


def hash_secret(secret: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    rounds = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def verify_secret(secret: str, encoded: str) -> bool:
    try:
        scheme, rounds_text, salt_hex, digest_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        if rounds < 100_000 or rounds > 2_000_000 or len(salt_hex) != 32 or len(digest_hex) != 64:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", secret.encode(), bytes.fromhex(salt_hex), rounds).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


class AuthStore:
    """SQLite adapter for development/integration; managed DB replaces this before launch."""

    def __init__(self, path: str = "neon_shield_auth.sqlite3", pepper: str | None = None) -> None:
        self.path = path
        self.pepper = pepper if pepper is not None else os.environ.get("NEON_AUTH_PEPPER", "")
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA busy_timeout=5000")
        self._db_lock = threading.RLock()
        self._migrate()

    def close(self) -> None:
        with self._db_lock:
            self._db.close()

    def _migrate(self) -> None:
        with self._db_lock:
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS users (subject_id TEXT PRIMARY KEY, identity_hash TEXT UNIQUE NOT NULL, credential_record TEXT NOT NULL, blocked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS devices (subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, trusted INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, PRIMARY KEY(subject_id, device_hash), FOREIGN KEY(subject_id) REFERENCES users(subject_id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS blocked_phones (phone_hash TEXT PRIMARY KEY, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (session_hash TEXT PRIMARY KEY, subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, issued_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(subject_id) REFERENCES users(subject_id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS audit_events (event_hash TEXT PRIMARY KEY, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, subject_id TEXT, device_fingerprint TEXT NOT NULL, previous_hash TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_sessions_subject ON sessions(subject_id);
                CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(occurred_at);
            """)

    def create_user(self, subject_id: str, identity: str, credential: str) -> None:
        with self._db_lock:
            self._db.execute("INSERT INTO users(subject_id,identity_hash,credential_record,created_at) VALUES(?,?,?,?)", (subject_id, _hash(identity.strip().lower(), self.pepper), hash_secret(credential), _now()))

    def trust_device(self, subject_id: str, device_id: str) -> None:
        with self._db_lock:
            self._db.execute("INSERT OR REPLACE INTO devices(subject_id,device_hash,trusted,created_at) VALUES(?,?,1,?)", (subject_id, _hash(device_id, self.pepper), _now()))

    def set_device_trusted(self, subject_id: str, device_id: str, trusted: bool) -> None:
        with self._db_lock:
            self._db.execute("UPDATE devices SET trusted=? WHERE subject_id=? AND device_hash=?", (1 if trusted else 0, subject_id, _hash(device_id, self.pepper)))

    def block_phone(self, phone: str) -> None:
        with self._db_lock:
            self._db.execute("INSERT OR IGNORE INTO blocked_phones(phone_hash,created_at) VALUES(?,?)", (_hash(phone, self.pepper), _now()))

    def find_user(self, identity: str):
        with self._db_lock:
            return self._db.execute("SELECT * FROM users WHERE identity_hash=?", (_hash(identity.strip().lower(), self.pepper),)).fetchone()

    def device_trusted(self, subject_id: str, device_id: str) -> bool:
        return self.device_hash_trusted(subject_id, _hash(device_id, self.pepper))

    def device_hash_trusted(self, subject_id: str, device_hash: str) -> bool:
        with self._db_lock:
            row = self._db.execute("SELECT trusted FROM devices WHERE subject_id=? AND device_hash=?", (subject_id, device_hash)).fetchone()
            return bool(row and row["trusted"])

    def identity_blocked(self, subject_id: str) -> bool:
        with self._db_lock:
            row = self._db.execute("SELECT blocked FROM users WHERE subject_id=?", (subject_id,)).fetchone()
            return bool(row and row["blocked"])

    def phone_blocked(self, phone: str) -> bool:
        with self._db_lock:
            return self._db.execute("SELECT 1 FROM blocked_phones WHERE phone_hash=?", (_hash(phone, self.pepper),)).fetchone() is not None

    def save_session(self, token: str, subject_id: str, device_id: str, issued_at: str, expires_at: str) -> None:
        self.save_session_hash(token, subject_id, _hash(device_id, self.pepper), issued_at, expires_at)

    def save_session_hash(self, token: str, subject_id: str, device_hash: str, issued_at: str, expires_at: str) -> None:
        with self._db_lock:
            self._db.execute("INSERT INTO sessions(session_hash,subject_id,device_hash,issued_at,expires_at) VALUES(?,?,?,?,?)", (_hash(token, self.pepper), subject_id, device_hash, issued_at, expires_at))

    def get_session(self, token: str):
        with self._db_lock:
            return self._db.execute("SELECT * FROM sessions WHERE session_hash=?", (_hash(token, self.pepper),)).fetchone()

    def revoke_session(self, token: str) -> None:
        with self._db_lock:
            self._db.execute("UPDATE sessions SET revoked=1 WHERE session_hash=?", (_hash(token, self.pepper),))

    def rotate_session(self, old_token: str, new_token: str, subject_id: str, device_hash: str, issued_at: str, expires_at: str) -> None:
        """Atomically revoke an existing session and issue its replacement."""
        with self._db_lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                old_hash = _hash(old_token, self.pepper)
                row = self._db.execute("SELECT revoked FROM sessions WHERE session_hash=?", (old_hash,)).fetchone()
                if row is None or row["revoked"]:
                    raise ValueError("session unavailable")
                self._db.execute("UPDATE sessions SET revoked=1 WHERE session_hash=?", (old_hash,))
                self._db.execute("INSERT INTO sessions(session_hash,subject_id,device_hash,issued_at,expires_at) VALUES(?,?,?,?,?)", (_hash(new_token, self.pepper), subject_id, device_hash, issued_at, expires_at))
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def last_audit_hash(self) -> str:
        with self._db_lock:
            row = self._db.execute("SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1").fetchone()
            return row["event_hash"] if row else "0" * 64

    def add_audit(self, event_type: str, subject_id: str | None, device_id: str) -> str:
        return self.add_audit_fingerprint(event_type, subject_id, _hash(device_id, self.pepper))

    def add_audit_fingerprint(self, event_type: str, subject_id: str | None, device_fingerprint: str) -> str:
        with self._db_lock:
            occurred_at = _now()
            previous_hash = self.last_audit_hash()
            event_hash = hashlib.sha256(f"{event_type}|{occurred_at}|{subject_id or ''}|{device_fingerprint}|{previous_hash}".encode()).hexdigest()
            self._db.execute("INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) VALUES(?,?,?,?,?,?)", (event_hash, event_type, occurred_at, subject_id, device_fingerprint, previous_hash))
            return event_hash
