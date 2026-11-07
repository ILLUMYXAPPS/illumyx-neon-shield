"""One-time, consent-based invitations for verified Premium Family households."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from entitlements import Package


class FamilyInvitationError(RuntimeError):
    """A Family invitation operation was rejected safely."""

    def __init__(self, reason: str, status: int = 400) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status


class FamilyInvitationService:
    """Create, accept and revoke hashed, expiring Family invitation tokens."""

    MAX_MEMBERS = 5
    INVITATION_TTL = timedelta(days=7)

    def __init__(self, connection_factory, subscription_repository, *, placeholder: str = "%s") -> None:
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        self._connect = connection_factory
        self._subscriptions = subscription_repository
        self._placeholder = placeholder

    def _sql(self, query: str) -> str:
        return query.replace("?", self._placeholder)

    @staticmethod
    def _row(cursor: Any, row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        if isinstance(row, dict):
            return dict(row)
        return dict(zip((column[0] for column in cursor.description), row, strict=False))

    def _begin(self, connection: Any) -> None:
        if self._placeholder == "?":
            connection.execute("BEGIN IMMEDIATE")

    def _lock_account(self, cursor: Any, subject_id: str) -> None:
        lock = "" if self._placeholder == "?" else " FOR UPDATE"
        cursor.execute(self._sql("SELECT subject_id FROM users WHERE subject_id=?" + lock), (subject_id,))
        if cursor.fetchone() is None:
            raise FamilyInvitationError("account_not_found", 404)

    def _require_family_entitlement(self, connection: Any, owner_subject_id: str) -> None:
        reader = getattr(self._subscriptions, "get_subscription_snapshot_in_transaction", None)
        if not callable(reader):
            raise FamilyInvitationError("transactional_subscription_reader_required", 503)
        snapshot = reader(connection, owner_subject_id)
        if snapshot.package is not Package.PREMIUM_FAMILY or not snapshot.is_current():
            raise FamilyInvitationError("active_premium_family_required", 403)

    def create_invitation(self, owner_subject_id: str) -> dict[str, str]:
        if not owner_subject_id or not owner_subject_id.strip():
            raise ValueError("authenticated owner is required")
        now = datetime.now(timezone.utc)
        created_at = now.isoformat()
        expires_at = (now + self.INVITATION_TTL).isoformat()
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        invitation_id = secrets.token_urlsafe(18)
        connection = self._connect()
        cursor = connection.cursor()
        try:
            self._begin(connection)
            self._lock_account(cursor, owner_subject_id)
            self._require_family_entitlement(connection, owner_subject_id)
            cursor.execute(self._sql(
                "SELECT owner_subject_id,role FROM family_memberships "
                "WHERE member_subject_id=? AND status='active'"
            ), (owner_subject_id,))
            existing = cursor.fetchone()
            if existing is not None:
                existing_owner = existing[0] if not isinstance(existing, dict) else existing["owner_subject_id"]
                existing_role = existing[1] if not isinstance(existing, dict) else existing["role"]
                if existing_owner != owner_subject_id or existing_role != "owner":
                    raise FamilyInvitationError("account_already_in_another_family", 409)
            else:
                cursor.execute(self._sql(
                    "INSERT INTO family_households(owner_subject_id,created_at) VALUES(?,?)"
                ), (owner_subject_id, created_at))
                cursor.execute(self._sql(
                    "INSERT INTO family_memberships(owner_subject_id,member_subject_id,role,status,created_at) "
                    "VALUES(?,?,'owner','active',?)"
                ), (owner_subject_id, owner_subject_id, created_at))
            cursor.execute(self._sql(
                "SELECT COUNT(*) FROM family_memberships WHERE owner_subject_id=? AND status='active'"
            ), (owner_subject_id,))
            active_count = int(cursor.fetchone()[0])
            cursor.execute(self._sql(
                "SELECT COUNT(*) FROM family_invitations "
                "WHERE owner_subject_id=? AND status='pending' AND expires_at>?"
            ), (owner_subject_id, created_at))
            pending_count = int(cursor.fetchone()[0])
            if active_count + pending_count >= self.MAX_MEMBERS:
                raise FamilyInvitationError("family_member_limit_reached", 409)
            cursor.execute(self._sql(
                "INSERT INTO family_invitations "
                "(invitation_id,owner_subject_id,token_hash,status,created_at,expires_at) "
                "VALUES(?,?,?,'pending',?,?)"
            ), (invitation_id, owner_subject_id, token_hash, created_at, expires_at))
            connection.commit()
            # The raw code is returned exactly once. Only its SHA-256 hash is stored.
            return {
                "invitation_id": invitation_id,
                "invitation_code": token,
                "expires_at": expires_at,
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def accept_invitation(self, member_subject_id: str, invitation_code: str) -> dict[str, str]:
        if not member_subject_id or not member_subject_id.strip():
            raise ValueError("authenticated member is required")
        if not isinstance(invitation_code, str) or not invitation_code or len(invitation_code) > 128:
            raise FamilyInvitationError("invalid_invitation")
        token_hash = hashlib.sha256(invitation_code.encode("utf-8")).hexdigest()
        connection = self._connect()
        cursor = connection.cursor()
        try:
            self._begin(connection)
            # Read the owner ID first without locking the invitation. All
            # membership operations lock account rows before invitation rows,
            # giving accept/revoke a consistent lock order and avoiding deadlocks.
            cursor.execute(self._sql(
                "SELECT invitation_id,owner_subject_id,status,expires_at FROM family_invitations "
                "WHERE token_hash=?"
            ), (token_hash,))
            invitation = self._row(cursor, cursor.fetchone())
            if invitation is None or invitation["status"] != "pending":
                raise FamilyInvitationError("invalid_or_used_invitation")
            owner_subject_id = invitation["owner_subject_id"]
            if owner_subject_id == member_subject_id:
                raise FamilyInvitationError("owner_cannot_accept_own_invitation", 409)
            for account_id in sorted((owner_subject_id, member_subject_id)):
                self._lock_account(cursor, account_id)
            lock = "" if self._placeholder == "?" else " FOR UPDATE"
            cursor.execute(self._sql(
                "SELECT invitation_id,owner_subject_id,status,expires_at FROM family_invitations "
                "WHERE token_hash=?" + lock
            ), (token_hash,))
            invitation = self._row(cursor, cursor.fetchone())
            now = datetime.now(timezone.utc)
            if invitation is None or invitation["status"] != "pending":
                raise FamilyInvitationError("invalid_or_used_invitation")
            if datetime.fromisoformat(invitation["expires_at"]) <= now:
                cursor.execute(self._sql(
                    "UPDATE family_invitations SET status='expired' WHERE invitation_id=? AND status='pending'"
                ), (invitation["invitation_id"],))
                connection.commit()
                raise FamilyInvitationError("invitation_expired", 410)
            self._require_family_entitlement(connection, owner_subject_id)
            cursor.execute(self._sql(
                "SELECT owner_subject_id,role,status FROM family_memberships "
                "WHERE member_subject_id=?"
            ), (member_subject_id,))
            prior_membership = self._row(cursor, cursor.fetchone())
            if prior_membership is not None and prior_membership["status"] == "active":
                raise FamilyInvitationError("account_already_in_a_family", 409)
            if prior_membership is not None and (
                prior_membership["owner_subject_id"] != owner_subject_id
                or prior_membership["role"] != "member"
            ):
                raise FamilyInvitationError("account_has_previous_family_membership", 409)
            cursor.execute(self._sql(
                "SELECT COUNT(*) FROM family_memberships WHERE owner_subject_id=? AND status='active'"
            ), (owner_subject_id,))
            if int(cursor.fetchone()[0]) >= self.MAX_MEMBERS:
                raise FamilyInvitationError("family_member_limit_reached", 409)
            cursor.execute(self._sql(
                "UPDATE family_invitations SET status='accepted',accepted_by=?,accepted_at=? "
                "WHERE invitation_id=? AND status='pending'"
            ), (member_subject_id, now.isoformat(), invitation["invitation_id"]))
            if getattr(cursor, "rowcount", 1) != 1:
                raise FamilyInvitationError("invalid_or_used_invitation", 409)
            if prior_membership is not None:
                cursor.execute(self._sql(
                    "UPDATE family_memberships SET status='active',created_at=? "
                    "WHERE owner_subject_id=? AND member_subject_id=? AND role='member' AND status='removed'"
                ), (now.isoformat(), owner_subject_id, member_subject_id))
                if getattr(cursor, "rowcount", 1) != 1:
                    raise FamilyInvitationError("account_membership_could_not_be_restored", 409)
            else:
                cursor.execute(self._sql(
                    "INSERT INTO family_memberships "
                    "(owner_subject_id,member_subject_id,role,status,created_at) "
                    "VALUES(?,?,'member','active',?)"
                ), (owner_subject_id, member_subject_id, now.isoformat()))
            connection.commit()
            return {"status": "accepted"}
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def list_invitations(self, owner_subject_id: str) -> tuple[dict[str, str], ...]:
        """List only non-secret invitation metadata for the authenticated household owner."""
        if not owner_subject_id or not owner_subject_id.strip():
            raise ValueError("authenticated owner is required")
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(self._sql(
                "SELECT owner_subject_id FROM family_households WHERE owner_subject_id=?"
            ), (owner_subject_id,))
            if cursor.fetchone() is None:
                return ()
            cursor.execute(self._sql(
                "SELECT invitation_id,status,created_at,expires_at FROM family_invitations "
                "WHERE owner_subject_id=? AND status='pending' ORDER BY created_at,invitation_id"
            ), (owner_subject_id,))
            return tuple(
                {
                    "invitation_id": row[0],
                    "status": row[1],
                    "created_at": row[2],
                    "expires_at": row[3],
                }
                for row in cursor.fetchall()
            )
        finally:
            cursor.close()
            connection.close()

    def revoke_invitation(self, owner_subject_id: str, invitation_id: str) -> bool:
        if not owner_subject_id or not owner_subject_id.strip() or not invitation_id:
            raise ValueError("authenticated owner and invitation are required")
        connection = self._connect()
        cursor = connection.cursor()
        try:
            self._begin(connection)
            self._lock_account(cursor, owner_subject_id)
            cursor.execute(self._sql(
                "UPDATE family_invitations SET status='revoked' "
                "WHERE invitation_id=? AND owner_subject_id=? AND status='pending'"
            ), (invitation_id, owner_subject_id))
            changed = getattr(cursor, "rowcount", 0) == 1
            connection.commit()
            return changed
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
