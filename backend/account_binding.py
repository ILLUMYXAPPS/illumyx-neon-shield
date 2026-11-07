"""Server-issued, durable account bindings for Apple and Google purchases."""
from __future__ import annotations
import uuid

class AccountBindingError(RuntimeError):
    """An authenticated account could not obtain its stable store binding."""

class AccountBindingRepository:
    """Issue one opaque UUID per authenticated Neon Shield subject.

    Pass only the subject_id from a server-validated session, never a client
    supplied request field. The UUID can be used as Apple's appAccountToken
    and Google's obfuscatedExternalAccountId by future provider adapters.
    """
    def __init__(self, connection_factory, *, placeholder: str = "%s") -> None:
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        self._connect = connection_factory
        self._placeholder = placeholder

    def _sql(self, query: str) -> str:
        return query.replace("?", self._placeholder)

    def get_or_create(self, *, authenticated_subject_id: str) -> str:
        if not isinstance(authenticated_subject_id, str) or not authenticated_subject_id.strip() or len(authenticated_subject_id) > 256:
            raise ValueError("authenticated subject_id is required")
        subject_id = authenticated_subject_id.strip()
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(self._sql("SELECT binding_id FROM store_account_bindings WHERE subject_id=?"), (subject_id,))
            row = cursor.fetchone()
            if row is not None:
                value = row[0] if not isinstance(row, dict) else row["binding_id"]
                connection.commit()
                return str(value)
            candidate = str(uuid.uuid4())
            cursor.execute(self._sql(
                "INSERT INTO store_account_bindings(subject_id,binding_id,created_at) "
                "VALUES(?,?,CURRENT_TIMESTAMP) ON CONFLICT(subject_id) DO NOTHING"
            ), (subject_id, candidate))
            connection.commit()
            cursor.execute(self._sql("SELECT binding_id FROM store_account_bindings WHERE subject_id=?"), (subject_id,))
            row = cursor.fetchone()
            if row is None:
                raise AccountBindingError("account binding could not be persisted")
            return str(row[0] if not isinstance(row, dict) else row["binding_id"])
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
