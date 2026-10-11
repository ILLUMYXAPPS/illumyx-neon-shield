"""Managed auth store with a PostgreSQL-serialized audit-chain head."""
from __future__ import annotations

import hashlib

from backend.managed_db_store import ManagedDbAuthStore


_ZERO_HASH = "0" * 64


class SerializedAuditManagedDbAuthStore(ManagedDbAuthStore):
    """Serialize audit appends by locking one durable chain-head row.

    Production deployments must apply migration 4 before serving requests.
    The row lock is held through both the audit event insert and head update.
    """

    def last_audit_hash(self) -> str:
        with self._cursor() as (_, cursor):
            cursor.execute(
                "SELECT last_event_hash FROM audit_chain_head WHERE chain_id=1"
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("audit chain head is missing; apply production migrations")
            return row[0]

    def add_audit_fingerprint(
        self, event_type: str, subject_id: str | None, device_fingerprint: str
    ) -> str:
        occurred_at = __import__("backend.managed_db_store", fromlist=["_now"])._now()
        with self._cursor() as (connection, cursor):
            cursor.execute(
                "SELECT last_event_hash FROM audit_chain_head WHERE chain_id=1"
                + self._audit_lock_clause
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("audit chain head is missing; apply production migrations")
            previous_hash = row[0]
            event_hash = hashlib.sha256(
                f"{event_type}|{occurred_at}|{subject_id or ''}|{device_fingerprint}|{previous_hash}".encode()
            ).hexdigest()
            cursor.execute(
                self._sql(
                    "INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) "
                    "VALUES(?,?,?,?,?,?)"
                ),
                (event_hash, event_type, occurred_at, subject_id, device_fingerprint, previous_hash),
            )
            cursor.execute(
                self._sql(
                    "UPDATE audit_chain_head SET last_event_hash=? WHERE chain_id=1"
                ),
                (event_hash,),
            )
            if getattr(cursor, "rowcount", 1) != 1:
                raise RuntimeError("audit chain head update did not affect exactly one row")
            connection.commit()
            return event_hash
