"""Resolve paid device allowances from verified subscriptions in the pairing transaction."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.device_limits import DeviceAllowance, DevicePackage


class DeviceAllowanceConfigurationError(RuntimeError):
    """Subscription or family data is not safe enough to authorize pairing."""


class VerifiedDeviceAllowanceResolver:
    """Read provider-verified entitlements and trusted family membership.

    resolve_in_transaction() must be called with the cursor that will also
    approve and insert the trusted device. The caller locks the owning
    subscription row, serializing concurrent device additions for that plan.
    """

    def __init__(self, *, placeholder: str = "%s", lock_clause: str = " FOR UPDATE"):
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        if lock_clause not in {"", " FOR UPDATE"}:
            raise ValueError("unsupported row lock clause")
        self._placeholder = placeholder
        self._lock_clause = lock_clause

    def _sql(self, query: str) -> str:
        return query.replace("?", self._placeholder)

    @staticmethod
    def _value(row, key: str, index: int):
        if isinstance(row, dict):
            return row[key]
        return row[index]

    def _active_subscription(self, cursor, subject_id: str, now: str):
        cursor.execute(
            self._sql(
                "SELECT subject_id, package, expires_at FROM verified_subscriptions "
                "WHERE subject_id=? AND revoked=0 AND (expires_at IS NULL OR expires_at>?) "
                "ORDER BY verified_at DESC LIMIT 1" + self._lock_clause
            ),
            (subject_id, now),
        )
        return cursor.fetchone()

    def resolve_in_transaction(self, cursor, subject_id: str) -> DeviceAllowance:
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise DeviceAllowanceConfigurationError("authenticated subject is required")
        now = datetime.now(timezone.utc).isoformat()

        # A family member must inherit the owner's current Family subscription,
        # never a package value supplied by the member's device.
        cursor.execute(
            self._sql(
                "SELECT owner_subject_id FROM family_memberships "
                "WHERE member_subject_id=? AND status='active'"
            ),
            (subject_id,),
        )
        membership = cursor.fetchone()
        owner_subject_id = (
            self._value(membership, "owner_subject_id", 0) if membership else subject_id
        )

        subscription = self._active_subscription(cursor, owner_subject_id, now)
        if subscription is None:
            return DeviceAllowance(DevicePackage.FREE, self._count_devices(cursor, subject_id))

        package = self._value(subscription, "package", 1)
        try:
            package = DevicePackage(package)
        except ValueError as exc:
            raise DeviceAllowanceConfigurationError("unknown verified subscription package") from exc

        member_count = self._count_devices(cursor, subject_id)
        if package is DevicePackage.PREMIUM:
            # A Family member cannot inherit a non-Family owner subscription.
            if membership:
                return DeviceAllowance(DevicePackage.FREE, member_count)
            return DeviceAllowance(DevicePackage.PREMIUM, member_count)

        if package is not DevicePackage.PREMIUM_FAMILY:
            return DeviceAllowance(DevicePackage.FREE, member_count)

        cursor.execute(
            self._sql(
                "SELECT COUNT(*) FROM family_memberships "
                "WHERE owner_subject_id=? AND status='active'"
            ),
            (owner_subject_id,),
        )
        member_rows = cursor.fetchone()
        active_members = int(
            member_rows[0] if not isinstance(member_rows, dict)
            else next(iter(member_rows.values()))
        )
        if active_members > 4:
            raise DeviceAllowanceConfigurationError(
                "family membership exceeds the five-person household limit"
            )
        if membership:
            cursor.execute(
                self._sql(
                    "SELECT 1 FROM family_memberships "
                    "WHERE owner_subject_id=? AND status='active'"
                ),
                (subject_id,),
            )
            if cursor.fetchone() is not None:
                raise DeviceAllowanceConfigurationError(
                    "an account cannot be both a family owner and member"
                )

        cursor.execute(
            self._sql(
                "SELECT COUNT(*) FROM devices d "
                "LEFT JOIN family_memberships fm "
                "ON fm.member_subject_id=d.subject_id AND fm.status='active' "
                "WHERE d.trusted=1 AND (d.subject_id=? OR fm.owner_subject_id=?)"
            ),
            (owner_subject_id, owner_subject_id),
        )
        total_row = cursor.fetchone()
        family_total = int(total_row[0] if not isinstance(total_row, dict) else next(iter(total_row.values())))
        return DeviceAllowance(DevicePackage.PREMIUM_FAMILY, member_count, family_total)

    @staticmethod
    def _count_devices(cursor, subject_id: str) -> int:
        cursor.execute(
            "SELECT COUNT(*) FROM devices WHERE subject_id=? AND trusted=1",
            (subject_id,),
        )
        row = cursor.fetchone()
        return int(row[0] if not isinstance(row, dict) else next(iter(row.values())))


class FamilyMembershipRepository:
    """Trusted server-side family membership writes after invitation acceptance.

    This repository intentionally exposes no client-controlled subject-ID
    endpoint. The calling invitation workflow must authenticate acceptance
    before invoking add_member().
    """

    def __init__(
        self, connection_factory, *, placeholder: str = "%s",
        lock_clause: str = " FOR UPDATE",
    ):
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        if lock_clause not in {"", " FOR UPDATE"}:
            raise ValueError("unsupported row lock clause")
        self._connect = connection_factory
        self._placeholder = placeholder
        self._lock_clause = lock_clause

    def _sql(self, query: str) -> str:
        return query.replace("?", self._placeholder)

    def add_member(self, *, owner_subject_id: str, member_subject_id: str) -> None:
        if (not owner_subject_id or not member_subject_id
                or owner_subject_id == member_subject_id):
            raise ValueError("distinct owner and member accounts are required")
        connection = self._connect()
        cursor = connection.cursor()
        try:
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                self._sql(
                    "SELECT package FROM verified_subscriptions "
                    "WHERE subject_id=? AND revoked=0 "
                    "AND (expires_at IS NULL OR expires_at>?) "
                    "ORDER BY verified_at DESC LIMIT 1" + self._lock_clause
                ),
                (owner_subject_id, now),
            )
            subscription = cursor.fetchone()
            if subscription is None or (
                subscription[0] if not isinstance(subscription, dict)
                else subscription["package"]
            ) != DevicePackage.PREMIUM_FAMILY.value:
                raise DeviceAllowanceConfigurationError(
                    "an active verified Premium Family subscription is required"
                )

            cursor.execute(
                self._sql(
                    "SELECT COUNT(*) FROM family_memberships "
                    "WHERE owner_subject_id=? AND status='active'"
                ),
                (owner_subject_id,),
            )
            count_row = cursor.fetchone()
            count = int(count_row[0] if not isinstance(count_row, dict)
                        else next(iter(count_row.values())))
            if count >= 4:
                raise DeviceAllowanceConfigurationError(
                    "Premium Family is limited to five people including the owner"
                )

            cursor.execute(
                self._sql(
                    "SELECT 1 FROM family_memberships "
                    "WHERE member_subject_id=? AND status='active'"
                ),
                (owner_subject_id,),
            )
            if cursor.fetchone() is not None:
                raise DeviceAllowanceConfigurationError(
                    "a family member cannot also own a family household"
                )
            cursor.execute(
                self._sql(
                    "SELECT 1 FROM family_memberships "
                    "WHERE member_subject_id=? AND status='active'"
                ),
                (member_subject_id,),
            )
            if cursor.fetchone() is not None:
                raise DeviceAllowanceConfigurationError(
                    "this account already belongs to a family"
                )
            cursor.execute(
                self._sql(
                    "SELECT 1 FROM family_memberships "
                    "WHERE owner_subject_id=? AND status='active'"
                ),
                (member_subject_id,),
            )
            if cursor.fetchone() is not None:
                raise DeviceAllowanceConfigurationError(
                    "a family owner cannot join another household"
                )

            cursor.execute(
                self._sql(
                    "INSERT INTO family_memberships "
                    "(owner_subject_id,member_subject_id,status,created_at,updated_at) "
                    "VALUES(?,?,'active',?,?) "
                    "ON CONFLICT(member_subject_id) DO UPDATE SET "
                    "owner_subject_id=excluded.owner_subject_id,status='active',"
                    "updated_at=excluded.updated_at"
                ),
                (owner_subject_id, member_subject_id, now, now),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def remove_member(self, *, owner_subject_id: str, member_subject_id: str) -> None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                self._sql(
                    "UPDATE family_memberships SET status='removed',updated_at=? "
                    "WHERE owner_subject_id=? AND member_subject_id=? AND status='active'"
                ),
                (now, owner_subject_id, member_subject_id),
            )
            if getattr(cursor, "rowcount", 1) != 1:
                raise DeviceAllowanceConfigurationError("active family membership not found")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
