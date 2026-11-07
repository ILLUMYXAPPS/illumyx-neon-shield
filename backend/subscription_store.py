"""Durable persistence for server-verified store subscriptions and notifications."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from entitlements import Package, SubscriptionSnapshot
from store_verification import StorePurchaseRequest, StoreProvider, VerifiedStorePurchase


class SubscriptionPersistenceError(RuntimeError):
    """Verified purchase facts could not be safely persisted."""


class StoreSubscriptionRepository:
    """DB-API repository. Call only after the provider verifier has authenticated evidence."""

    def __init__(self, connection_factory, *, pepper: str, placeholder: str = "%s") -> None:
        if not pepper:
            raise RuntimeError("subscription repository requires a deployment-supplied pepper")
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        self._connect = connection_factory
        self._pepper = pepper.encode("utf-8")
        self._placeholder = placeholder

    def _sql(self, query: str) -> str:
        return query.replace("?", self._placeholder)

    def _token_hash(self, token: str) -> str:
        if not token or not token.strip():
            raise ValueError("purchase token is required")
        return hmac.new(self._pepper, token.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _row(cursor: Any, row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        if isinstance(row, dict):
            return dict(row)
        return dict(zip((column[0] for column in cursor.description), row, strict=False))

    def save_verified_purchase(
        self, *, subject_id: str, request: StorePurchaseRequest,
        purchase: VerifiedStorePurchase, package: Package,
        verified_at: datetime | None = None,
    ) -> None:
        """Save verified facts, never raw purchase tokens; transaction IDs cannot move accounts."""
        if not subject_id or not subject_id.strip():
            raise ValueError("authenticated subject_id is required")
        if package not in {Package.PREMIUM, Package.PREMIUM_FAMILY}:
            raise ValueError("only paid packages can be persisted")
        if (request.provider is not purchase.provider
            or request.product_id != purchase.product_id
            or request.application_id != purchase.application_id
            or request.account_binding_id != purchase.account_binding_id):
            raise SubscriptionPersistenceError("verified purchase does not match request")
        now = verified_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("verified_at must be timezone-aware")
        # Normalize ordering timestamps so text comparisons are chronological
        # across PostgreSQL/SQLite and callers using different UTC offsets.
        now = now.astimezone(timezone.utc)
        expiry = purchase.expires_at.astimezone(timezone.utc).isoformat() if purchase.expires_at else None
        connection = self._connect()
        cursor = connection.cursor()
        try:
            # Serialize entitlement changes with pairing approvals, which lock this
            # account row before reading the verified subscription snapshot.
            if self._placeholder == "?":
                connection.execute("BEGIN IMMEDIATE")
            else:
                cursor.execute(
                    self._sql("SELECT subject_id FROM users WHERE subject_id=? FOR UPDATE"),
                    (subject_id,),
                )
                if cursor.fetchone() is None:
                    raise SubscriptionPersistenceError("authenticated account does not exist")
            if (purchase.provider is StoreProvider.GOOGLE_PLAY
                    and purchase.replaces_original_transaction_id):
                cursor.execute(self._sql(
                    "SELECT subject_id,account_binding_id FROM verified_subscriptions "
                    "WHERE provider=? AND original_transaction_id=?"),
                    (StoreProvider.GOOGLE_PLAY.value,
                     purchase.replaces_original_transaction_id))
                linked_row = self._row(cursor, cursor.fetchone())
                if linked_row is not None and (
                    linked_row["subject_id"] != subject_id
                    or linked_row["account_binding_id"] != purchase.account_binding_id
                ):
                    raise SubscriptionPersistenceError(
                        "linked Google purchase is already bound to another account"
                    )
            cursor.execute(self._sql(
                "INSERT INTO verified_subscriptions "
                "(subscription_id,subject_id,provider,application_id,product_id,package,environment,"
                "account_binding_id,transaction_id,original_transaction_id,purchase_token_hash,"
                "expires_at,revoked,verified_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(provider,original_transaction_id) DO UPDATE SET "
                "application_id=excluded.application_id,product_id=excluded.product_id,"
                "package=excluded.package,environment=excluded.environment,"
                "transaction_id=excluded.transaction_id,purchase_token_hash=excluded.purchase_token_hash,"
                "expires_at=excluded.expires_at,revoked=excluded.revoked,"
                "verified_at=excluded.verified_at,updated_at=excluded.updated_at "
                "WHERE verified_subscriptions.subject_id=excluded.subject_id "
                "AND verified_subscriptions.account_binding_id=excluded.account_binding_id "
                "AND verified_subscriptions.verified_at<=excluded.verified_at"),
                (purchase.original_transaction_id, subject_id, purchase.provider.value,
                 purchase.application_id, purchase.product_id, package.value,
                 purchase.environment.lower(), purchase.account_binding_id,
                 purchase.transaction_id, purchase.original_transaction_id,
                 self._token_hash(request.purchase_token), expiry, int(purchase.revoked),
                 now.isoformat(), now.isoformat()))
            changed = getattr(cursor, "rowcount", 1)
            if changed == 0:
                cursor.execute(self._sql(
                    "SELECT subject_id,account_binding_id,verified_at FROM verified_subscriptions "
                    "WHERE provider=? AND original_transaction_id=?"
                ), (purchase.provider.value, purchase.original_transaction_id))
                existing = self._row(cursor, cursor.fetchone())
                if existing is None or (
                    existing["subject_id"] != subject_id
                    or existing["account_binding_id"] != purchase.account_binding_id
                ):
                    raise SubscriptionPersistenceError(
                        "transaction is already bound to another account"
                    )
                existing_time = datetime.fromisoformat(existing["verified_at"])
                if existing_time > now:
                    # A delayed provider notification must never roll back a
                    # newer verified state for the same subscription chain.
                    connection.commit()
                    return False
                raise SubscriptionPersistenceError(
                    "verified subscription update was not applied"
                )

            # Only revoke a superseded Google token after the replacement
            # purchase won the monotonic update check above.
            if (purchase.provider is StoreProvider.GOOGLE_PLAY
                    and purchase.replaces_original_transaction_id):
                cursor.execute(self._sql(
                    "UPDATE verified_subscriptions SET revoked=1,updated_at=? "
                    "WHERE provider=? AND original_transaction_id=? "
                    "AND subject_id=? AND account_binding_id=?"
                ), (now.isoformat(), StoreProvider.GOOGLE_PLAY.value,
                    purchase.replaces_original_transaction_id, subject_id,
                    purchase.account_binding_id))
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def get_subscription_snapshot_in_transaction(
        self, connection: Any, subject_id: str, *, now: datetime | None = None
    ) -> SubscriptionSnapshot:
        """Read the authoritative active package using a caller-owned transaction."""
        if not subject_id or not subject_id.strip():
            raise ValueError("authenticated subject_id is required")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        cursor = connection.cursor()
        try:
            cursor.execute(self._sql(
                "SELECT package,expires_at FROM verified_subscriptions WHERE subject_id=? AND revoked=0 "
                "AND (expires_at IS NULL OR expires_at>?) "
                "ORDER BY CASE package WHEN 'premium_family' THEN 2 ELSE 1 END DESC,expires_at DESC"),
                (subject_id, current.isoformat()))
            row = self._row(cursor, cursor.fetchone())
            if row is None:
                return SubscriptionSnapshot(Package.FREE, active=True)
            expiry = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            return SubscriptionSnapshot(Package(row["package"]), active=True, expires_at=expiry)
        finally:
            cursor.close()

    def get_subscription_snapshot(self, subject_id: str, *, now: datetime | None = None) -> SubscriptionSnapshot:
        """Read an active server-stored paid package; otherwise return Basic/Free."""
        connection = self._connect()
        try:
            return self.get_subscription_snapshot_in_transaction(
                connection, subject_id, now=now
            )
        finally:
            connection.close()

    def record_notification(
        self, *, provider: StoreProvider, event_id: str, event_type: str,
        payload: bytes, received_at: datetime | None = None,
    ) -> bool:
        """Record an already-authenticated provider event once; duplicates return False."""
        if not isinstance(provider, StoreProvider) or not event_id or not event_type:
            raise ValueError("provider, event ID and event type are required")
        if not isinstance(payload, bytes):
            raise TypeError("notification payload must be bytes")
        when = received_at or datetime.now(timezone.utc)
        if when.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        digest = hashlib.sha256(payload).hexdigest()
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(self._sql(
                "INSERT INTO store_notification_events "
                "(provider,event_id,event_type,payload_hash,received_at,processing_status) "
                "VALUES (?,?,?,?,?,'received') ON CONFLICT(provider,event_id) DO NOTHING"),
                (provider.value, event_id, event_type, digest, when.isoformat()))
            inserted = getattr(cursor, "rowcount", 1) == 1
            connection.commit()
            return inserted
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def finish_notification(
        self, *, provider: StoreProvider, event_id: str, processed: bool,
        processed_at: datetime | None = None,
    ) -> bool:
        """Finalize a received event once; never changes a previously-final event."""
        when = processed_at or datetime.now(timezone.utc)
        if not isinstance(provider, StoreProvider) or not event_id or when.tzinfo is None:
            raise ValueError("provider, event ID and timezone-aware timestamp are required")
        status = "processed" if processed else "rejected"
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(self._sql(
                "UPDATE store_notification_events SET processing_status=?,processed_at=? "
                "WHERE provider=? AND event_id=? AND processing_status='received'"),
                (status, when.isoformat(), provider.value, event_id))
            changed = getattr(cursor, "rowcount", 0) == 1
            connection.commit()
            return changed
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
