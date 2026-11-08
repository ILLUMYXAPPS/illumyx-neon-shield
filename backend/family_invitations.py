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
    RATE_LIMITS = {
        "create": (5, 3600),
        "accept": (10, 900),
        "list": (60, 60),
        "revoke": (20, 3600),
    }

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

    def _reserve_rate_limit(self, action: str, subject_id: str) -> None:
        """Persist an operation reservation independently so rejected requests count too."""
        limit, window_seconds = self.RATE_LIMITS[action]
        identity_hash = hashlib.sha256(
            f"family-invitations:{action}:{subject_id}".encode("utf-8")
        ).hexdigest()
        now = datetime.now(timezone.utc)
        now_text = now.isoformat()
        connection = self._connect()
        cursor = connection.cursor()
        try:
            self._begin(connection)
            # Lock the authenticated account first. This serializes first-use
            # reservations too, when no rate-limit row exists yet.
            self._lock_account(cursor, subject_id)
            lock = "" if self._placeholder == "?" else " FOR UPDATE"
            cursor.execute(self._sql(
                "SELECT failure_count,window_started_at FROM sign_in_rate_limits WHERE identity_hash=?" + lock
            ), (identity_hash,))
            row = cursor.fetchone()
            if row is None:
                count = 1
                cursor.execute(self._sql(
                    "INSERT INTO sign_in_rate_limits(identity_hash,failure_count,window_started_at) VALUES(?,?,?)"
                ), (identity_hash, count, now_text))
            else:
                count_value = row[0] if not isinstance(row, dict) else row["failure_count"]
                started_value = row[1] if not isinstance(row, dict) else row["window_started_at"]
                if now.timestamp() - datetime.fromisoformat(started_value).timestamp() >= window_seconds:
                    count = 1
                    cursor.execute(self._sql(
                        "UPDATE sign_in_rate_limits SET failure_count=1,window_started_at=? WHERE identity_hash=?"
                    ), (now_text, identity_hash))
                else:
                    count = int(count_value) + 1
                    cursor.execute(self._sql(
                        "UPDATE sign_in_rate_limits SET failure_count=? WHERE identity_hash=?"
                    ), (count, identity_hash))
            connection.commit()
            if count > limit:
                raise FamilyInvitationError("family_invitation_rate_limited", 429)
        except FamilyInvitationError:
            raise
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def _audit(cursor: Any, placeholder: str, event_type: str, subject_id: str) -> None:
        """Append a privacy-safe event to the existing hash-chained audit ledger."""
        occurred_at = datetime.now(timezone.utc).isoformat()
        # Serialize all writers on the same stable chain-head row. A SELECT of
        # the latest event is not sufficient when the ledger is empty or two
        # unrelated accounts append concurrently.
        cursor.execute("UPDATE audit_chain_head SET event_hash=event_hash WHERE chain_id=1")
        lock = "" if placeholder == "?" else " FOR UPDATE"
        cursor.execute("SELECT event_hash FROM audit_chain_head WHERE chain_id=1" + lock)
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("audit chain head is missing; run production migrations")
        previous_hash = row[0] if not isinstance(row, dict) else row["event_hash"]
        fingerprint = hashlib.sha256(f"family-actor:{subject_id}".encode("utf-8")).hexdigest()
        event_hash = hashlib.sha256(
            f"{event_type}|{occurred_at}|{subject_id}|{fingerprint}|{previous_hash}".encode("utf-8")
        ).hexdigest()
        marker = placeholder
        cursor.execute(
            "INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) "
            f"VALUES({marker},{marker},{marker},{marker},{marker},{marker})",
            (event_hash, event_type, occurred_at, subject_id, fingerprint, previous_hash),
        )
        cursor.execute(
            "UPDATE audit_chain_head SET event_hash=? WHERE chain_id=1".replace("?", placeholder),
            (event_hash,),
        )
        if getattr(cursor, "rowcount", 1) != 1:
            raise RuntimeError("audit chain head update did not affect exactly one row")

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
        self._reserve_rate_limit("create", owner_subject_id)
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
            self._audit(cursor, self._placeholder, "family_invitation_created", owner_subject_id)
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
        self._reserve_rate_limit("accept", member_subject_id)
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
                self._audit(cursor, self._placeholder, "family_invitation_expired", owner_subject_id)
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
            self._audit(cursor, self._placeholder, "family_invitation_accepted", member_subject_id)
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
        self._reserve_rate_limit("list", owner_subject_id)
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
                "WHERE owner_subject_id=? AND status='pending' AND expires_at>? "
                "ORDER BY created_at,invitation_id"
            ), (owner_subject_id, datetime.now(timezone.utc).isoformat()))
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
        self._reserve_rate_limit("revoke", owner_subject_id)
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
            if changed:
                self._audit(cursor, self._placeholder, "family_invitation_revoked", owner_subject_id)
            connection.commit()
            return changed
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
