"""Trusted family membership and subscription-derived device allowances.

Membership writes are an internal server boundary. Never expose these repository
methods directly to an unauthenticated or client-authorized endpoint.
"""
from __future__ import annotations

from typing import Any

from backend.device_limits import DeviceAllowance, DevicePackage
from entitlements import Package


class FamilyMembershipError(RuntimeError):
    """A family membership change violates household invariants."""


class FamilyMembershipRepository:
    """Persist household roles without exposing one member's private account data."""

    MAX_MEMBERS = 5

    def __init__(self, connection_factory, *, placeholder: str = "%s", lock_clause: str | None = None) -> None:
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        if lock_clause not in {None, "", " FOR UPDATE"}:
            raise ValueError("unsupported family membership lock clause")
        self._connect = connection_factory
        self._placeholder = placeholder
        self._lock_clause = lock_clause if lock_clause is not None else ("" if placeholder == "?" else " FOR UPDATE")

    def _sql(self, query: str) -> str:
        return query.replace("?", self._placeholder)

    @staticmethod
    def _row(cursor: Any, row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        if isinstance(row, dict):
            return dict(row)
        return dict(zip((column[0] for column in cursor.description), row, strict=False))

    def create_household(self, owner_subject_id: str, *, created_at: str) -> None:
        if not owner_subject_id or not owner_subject_id.strip():
            raise ValueError("owner subject is required")
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(
                self._sql("INSERT INTO family_households(owner_subject_id,created_at) VALUES(?,?)"),
                (owner_subject_id, created_at),
            )
            cursor.execute(
                self._sql(
                    "INSERT INTO family_memberships(owner_subject_id,member_subject_id,role,status,created_at) "
                    "VALUES(?,?,'owner','active',?)"
                ),
                (owner_subject_id, owner_subject_id, created_at),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def add_member(self, owner_subject_id: str, member_subject_id: str, *, created_at: str) -> None:
        if not owner_subject_id or not member_subject_id or owner_subject_id == member_subject_id:
            raise ValueError("a distinct owner and member are required")
        connection = self._connect()
        cursor = connection.cursor()
        try:
            if self._placeholder == "?":
                connection.execute("BEGIN IMMEDIATE")
            cursor.execute(
                self._sql("SELECT owner_subject_id FROM family_households WHERE owner_subject_id=?" + self._lock_clause),
                (owner_subject_id,),
            )
            if cursor.fetchone() is None:
                raise FamilyMembershipError("household_not_found")
            cursor.execute(
                self._sql("SELECT COUNT(*) FROM family_memberships WHERE owner_subject_id=? AND status='active'"),
                (owner_subject_id,),
            )
            if int(cursor.fetchone()[0]) >= self.MAX_MEMBERS:
                raise FamilyMembershipError("family_member_limit_reached")
            cursor.execute(
                self._sql(
                    "INSERT INTO family_memberships(owner_subject_id,member_subject_id,role,status,created_at) "
                    "VALUES(?,?,'member','active',?)"
                ),
                (owner_subject_id, member_subject_id, created_at),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def remove_member(self, owner_subject_id: str, member_subject_id: str) -> bool:
        if owner_subject_id == member_subject_id:
            raise FamilyMembershipError("household_owner_cannot_be_removed")
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(
                self._sql(
                    "UPDATE family_memberships SET status='removed' "
                    "WHERE owner_subject_id=? AND member_subject_id=? AND role='member' AND status='active'"
                ),
                (owner_subject_id, member_subject_id),
            )
            changed = getattr(cursor, "rowcount", 0) == 1
            connection.commit()
            return changed
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def household_owner_for(self, member_subject_id: str) -> str | None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(
                self._sql(
                    "SELECT owner_subject_id FROM family_memberships "
                    "WHERE member_subject_id=? AND status='active'"
                ),
                (member_subject_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            cursor.close()
            connection.close()

    def active_members(self, owner_subject_id: str) -> tuple[str, ...]:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(
                self._sql(
                    "SELECT member_subject_id FROM family_memberships "
                    "WHERE owner_subject_id=? AND status='active' ORDER BY created_at,member_subject_id"
                ),
                (owner_subject_id,),
            )
            return tuple(row[0] for row in cursor.fetchall())
        finally:
            cursor.close()
            connection.close()


class StoreDeviceAllowanceResolver:
    """Resolve a member's allowance from verified subscriptions and trusted DB records."""

    def __init__(self, connection_factory, subscription_repository, family_repository, *, placeholder: str = "%s"):
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        self._connect = connection_factory
        self._placeholder = placeholder
        self._subscriptions = subscription_repository
        self._families = family_repository

    def _sql(self, query: str) -> str:
        return query.replace("?", self._placeholder)

    def _trusted_device_count(self, subject_ids: tuple[str, ...]) -> int:
        if not subject_ids:
            return 0
        connection = self._connect()
        cursor = connection.cursor()
        try:
            placeholders = ",".join("?" for _ in subject_ids)
            cursor.execute(
                self._sql(
                    "SELECT COUNT(*) FROM devices WHERE trusted=1 AND subject_id IN (" + placeholders + ")"
                ),
                subject_ids,
            )
            return int(cursor.fetchone()[0])
        finally:
            cursor.close()
            connection.close()

    def __call__(self, subject_id: str, request_id: str | None = None) -> DeviceAllowance:
        if not subject_id or not subject_id.strip():
            raise ValueError("authenticated subject is required")
        owner = self._families.household_owner_for(subject_id)
        if owner is not None:
            snapshot = self._subscriptions.get_subscription_snapshot(owner)
            if snapshot.package is not Package.PREMIUM_FAMILY or not snapshot.is_current():
                return DeviceAllowance(DevicePackage.FREE, self._trusted_device_count((subject_id,)))
            members = self._families.active_members(owner)
            if subject_id not in members or len(members) > FamilyMembershipRepository.MAX_MEMBERS:
                raise FamilyMembershipError("invalid_family_membership")
            return DeviceAllowance(
                DevicePackage.PREMIUM_FAMILY,
                self._trusted_device_count((subject_id,)),
                self._trusted_device_count(members),
            )

        snapshot = self._subscriptions.get_subscription_snapshot(subject_id)
        package = {
            Package.PREMIUM: DevicePackage.PREMIUM,
            Package.PREMIUM_FAMILY: DevicePackage.PREMIUM_FAMILY,
            Package.FREE: DevicePackage.FREE,
        }[snapshot.package]
        if package is DevicePackage.PREMIUM_FAMILY:
            members = self._families.active_members(subject_id)
            if not members or subject_id not in members:
                raise FamilyMembershipError("family_owner_membership_missing")
            return DeviceAllowance(
                package,
                self._trusted_device_count((subject_id,)),
                self._trusted_device_count(members),
            )
        return DeviceAllowance(package, self._trusted_device_count((subject_id,)))
