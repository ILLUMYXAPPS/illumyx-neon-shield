"""DB-API managed persistence adapter for the production auth boundary."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from backend.managed_store import ManagedAuthStore
from backend.store import _hash, hash_secret


_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS users (subject_id TEXT PRIMARY KEY, identity_hash TEXT UNIQUE NOT NULL, credential_record TEXT NOT NULL, blocked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS devices (subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, trusted INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, PRIMARY KEY(subject_id, device_hash), FOREIGN KEY(subject_id) REFERENCES users(subject_id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS blocked_phones (phone_hash TEXT PRIMARY KEY, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS sessions (session_hash TEXT PRIMARY KEY, subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, issued_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(subject_id) REFERENCES users(subject_id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS sign_in_rate_limits (identity_hash TEXT PRIMARY KEY, failure_count INTEGER NOT NULL, window_started_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS audit_events (event_hash TEXT PRIMARY KEY, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, subject_id TEXT, device_fingerprint TEXT NOT NULL, previous_hash TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS idx_managed_sessions_subject ON sessions(subject_id)",
    "CREATE INDEX IF NOT EXISTS idx_managed_audit_time ON audit_events(occurred_at)",
)

_ALLOWED_AUDIT_LOCK_CLAUSES = {"", " FOR UPDATE"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ManagedDbAuthStore(ManagedAuthStore):
    """Concrete managed-database adapter using an injected DB-API connection factory."""

    def __init__(
        self,
        connection_factory: Callable[[], Any],
        *,
        pepper: str,
        placeholder: str = "%s",
        audit_lock_clause: str = " FOR UPDATE",
    ) -> None:
        if not pepper:
            raise RuntimeError("managed database auth store requires a deployment-supplied pepper")
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        if audit_lock_clause not in _ALLOWED_AUDIT_LOCK_CLAUSES:
            raise ValueError("unsupported audit lock clause")
        self._connection_factory = connection_factory
        self._pepper = pepper
        self._placeholder = placeholder
        self._audit_lock_clause = audit_lock_clause

    def _sql(self, query: str) -> str:
        return query.replace("?", self._placeholder)

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        connection = self._connection_factory()
        try:
            yield connection
        except Exception:
            rollback = getattr(connection, "rollback", None)
            if rollback is not None:
                rollback()
            raise
        finally:
            close = getattr(connection, "close", None)
            if close is not None:
                close()

    @contextmanager
    def _cursor(self) -> Iterator[tuple[Any, Any]]:
        with self._connection() as connection:
            cursor = connection.cursor()
            try:
                yield connection, cursor
            finally:
                close = getattr(cursor, "close", None)
                if close is not None:
                    close()

    @staticmethod
    def _row(cursor: Any, row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        if isinstance(row, dict):
            return dict(row)
        columns = [item[0] for item in cursor.description]
        return dict(zip(columns, row, strict=False))

    def migrate(self) -> None:
        """Create the adapter schema; production migrations should be versioned separately."""
        with self._cursor() as (connection, cursor):
            for statement in _SCHEMA:
                cursor.execute(statement)
            connection.commit()

    def create_user(self, subject_id: str, identity: str, credential: str) -> None:
        with self._cursor() as (connection, cursor):
            cursor.execute(self._sql("INSERT INTO users(subject_id,identity_hash,credential_record,created_at) VALUES(?,?,?,?)"), (subject_id, _hash(identity.strip().lower(), self._pepper), hash_secret(credential), _now()))
            connection.commit()

    def trust_device(self, subject_id: str, device_id: str) -> None:
        with self._cursor() as (connection, cursor):
            cursor.execute(self._sql("INSERT INTO devices(subject_id,device_hash,trusted,created_at) VALUES(?,?,1,?) ON CONFLICT(subject_id,device_hash) DO UPDATE SET trusted=1,created_at=excluded.created_at"), (subject_id, _hash(device_id, self._pepper), _now()))
            connection.commit()

    def set_device_trusted(self, subject_id: str, device_id: str, trusted: bool) -> None:
        with self._cursor() as (connection, cursor):
            cursor.execute(self._sql("UPDATE devices SET trusted=? WHERE subject_id=? AND device_hash=?"), (1 if trusted else 0, subject_id, _hash(device_id, self._pepper)))
            connection.commit()

    def block_phone(self, phone: str) -> None:
        with self._cursor() as (connection, cursor):
            cursor.execute(self._sql("INSERT INTO blocked_phones(phone_hash,created_at) VALUES(?,?) ON CONFLICT(phone_hash) DO NOTHING"), (_hash(phone, self._pepper), _now()))
            connection.commit()

    def find_user(self, identity: str) -> Any:
        with self._cursor() as (_, cursor):
            cursor.execute(self._sql("SELECT * FROM users WHERE identity_hash=?"), (_hash(identity.strip().lower(), self._pepper),))
            return self._row(cursor, cursor.fetchone())

    def device_trusted(self, subject_id: str, device_id: str) -> bool:
        return self.device_hash_trusted(subject_id, _hash(device_id, self._pepper))

    def device_hash_trusted(self, subject_id: str, device_hash: str) -> bool:
        with self._cursor() as (_, cursor):
            cursor.execute(self._sql("SELECT trusted FROM devices WHERE subject_id=? AND device_hash=?"), (subject_id, device_hash))
            row = cursor.fetchone()
            return bool(row and row[0])

    def identity_blocked(self, subject_id: str) -> bool:
        with self._cursor() as (_, cursor):
            cursor.execute(self._sql("SELECT blocked FROM users WHERE subject_id=?"), (subject_id,))
            row = cursor.fetchone()
            return bool(row and row[0])

    def phone_blocked(self, phone: str) -> bool:
        with self._cursor() as (_, cursor):
            cursor.execute(self._sql("SELECT 1 FROM blocked_phones WHERE phone_hash=?"), (_hash(phone, self._pepper),))
            return cursor.fetchone() is not None

    def save_session(self, token: str, subject_id: str, device_id: str, issued_at: str, expires_at: str) -> None:
        self.save_session_hash(token, subject_id, _hash(device_id, self._pepper), issued_at, expires_at)

    def save_session_hash(self, token: str, subject_id: str, device_hash: str, issued_at: str, expires_at: str) -> None:
        with self._cursor() as (connection, cursor):
            cursor.execute(self._sql("INSERT INTO sessions(session_hash,subject_id,device_hash,issued_at,expires_at) VALUES(?,?,?,?,?)"), (_hash(token, self._pepper), subject_id, device_hash, issued_at, expires_at))
            connection.commit()

    def get_session(self, token: str) -> Any:
        with self._cursor() as (_, cursor):
            cursor.execute(self._sql("SELECT * FROM sessions WHERE session_hash=?"), (_hash(token, self._pepper),))
            return self._row(cursor, cursor.fetchone())

    def revoke_session(self, token: str) -> None:
        with self._cursor() as (connection, cursor):
            cursor.execute(self._sql("UPDATE sessions SET revoked=1 WHERE session_hash=?"), (_hash(token, self._pepper),))
            connection.commit()

    def rotate_session(self, token: str, new_token: str, issued_at: str, expires_at: str) -> Any:
        """Atomically consume one live session and create its replacement."""
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(self._sql("SELECT subject_id, device_hash, expires_at FROM sessions WHERE session_hash=? AND revoked=0" + self._audit_lock_clause), (_hash(token, self._pepper),))
            row = self._row(cursor, cursor.fetchone())
            if row is None or datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
                connection.rollback()
                return None
            cursor.execute(self._sql("UPDATE sessions SET revoked=1 WHERE session_hash=? AND revoked=0"), (_hash(token, self._pepper),))
            if getattr(cursor, "rowcount", 1) != 1:
                connection.rollback()
                return None
            cursor.execute(self._sql("INSERT INTO sessions(session_hash,subject_id,device_hash,issued_at,expires_at) VALUES(?,?,?,?,?)"), (_hash(new_token, self._pepper), row["subject_id"], row["device_hash"], issued_at, expires_at))
            connection.commit()
            return row
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(cursor, "close", None)
            if close is not None:
                close()
            close_connection = getattr(connection, "close", None)
            if close_connection is not None:
                close_connection()

    def sign_in_rate_limited(self, identity: str, now: str, window_seconds: int, max_sign_ins: int) -> bool:
        identity_hash = _hash(identity.strip().lower(), self._pepper)
        with self._cursor() as (connection, cursor):
            cursor.execute(self._sql("SELECT failure_count, window_started_at FROM sign_in_rate_limits WHERE identity_hash=?"), (identity_hash,))
            row = cursor.fetchone()
            if row is None:
                return False
            if datetime.fromisoformat(now).timestamp() - datetime.fromisoformat(row[1]).timestamp() >= window_seconds:
                cursor.execute(self._sql("DELETE FROM sign_in_rate_limits WHERE identity_hash=?"), (identity_hash,))
                connection.commit()
                return False
            return int(row[0]) >= max_sign_ins

    def record_sign_in_failure(self, identity: str, now: str, window_seconds: int, max_sign_ins: int) -> None:
        identity_hash = _hash(identity.strip().lower(), self._pepper)
        now_dt = datetime.fromisoformat(now)
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(self._sql("SELECT failure_count, window_started_at FROM sign_in_rate_limits WHERE identity_hash=?" + self._audit_lock_clause), (identity_hash,))
            row = cursor.fetchone()
            if row is None or now_dt.timestamp() - datetime.fromisoformat(row[1]).timestamp() >= window_seconds:
                cursor.execute(self._sql("INSERT INTO sign_in_rate_limits(identity_hash,failure_count,window_started_at) VALUES(?,?,?) ON CONFLICT(identity_hash) DO UPDATE SET failure_count=1,window_started_at=excluded.window_started_at"), (identity_hash, 1, now))
            elif int(row[0]) < max_sign_ins:
                cursor.execute(self._sql("UPDATE sign_in_rate_limits SET failure_count=failure_count+1 WHERE identity_hash=?"), (identity_hash,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(cursor, "close", None)
            if close is not None:
                close()
            close_connection = getattr(connection, "close", None)
            if close_connection is not None:
                close_connection()

    def clear_sign_in_failures(self, identity: str) -> None:
        with self._cursor() as (connection, cursor):
            cursor.execute(self._sql("DELETE FROM sign_in_rate_limits WHERE identity_hash=?"), (_hash(identity.strip().lower(), self._pepper),))
            connection.commit()

    def last_audit_hash(self) -> str:
        with self._cursor() as (_, cursor):
            cursor.execute("SELECT event_hash FROM audit_events ORDER BY occurred_at DESC, event_hash DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else "0" * 64

    def add_audit(self, event_type: str, subject_id: str | None, device_id: str) -> str:
        return self.add_audit_fingerprint(event_type, subject_id, _hash(device_id, self._pepper))

    def add_audit_fingerprint(self, event_type: str, subject_id: str | None, device_fingerprint: str) -> str:
        occurred_at = _now()
        with self._cursor() as (connection, cursor):
            cursor.execute("SELECT event_hash FROM audit_events ORDER BY occurred_at DESC, event_hash DESC LIMIT 1" + self._audit_lock_clause)
            row = cursor.fetchone()
            previous_hash = row[0] if row else "0" * 64
            event_hash = hashlib.sha256(f"{event_type}|{occurred_at}|{subject_id or ''}|{device_fingerprint}|{previous_hash}".encode()).hexdigest()
            cursor.execute(self._sql("INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) VALUES(?,?,?,?,?,?)"), (event_hash, event_type, occurred_at, subject_id, device_fingerprint, previous_hash))
            connection.commit()
            return event_hash
