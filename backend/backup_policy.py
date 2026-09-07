"""Fail-closed backup and restore controls for production deployments.

This module defines the application-independent contract that a deployment
must satisfy. It does not create backups, restore databases, or claim that
managed backup infrastructure exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse


@dataclass(frozen=True)
class BackupPolicy:
    """Minimum recovery expectations for a production deployment."""

    rpo_minutes: int = 15
    rto_minutes: int = 60
    retention_days: int = 35
    encryption_required: bool = True
    restore_test_required: bool = True

    def __post_init__(self) -> None:
        if self.rpo_minutes < 1:
            raise ValueError("RPO must be at least 1 minute")
        if self.rto_minutes < 1:
            raise ValueError("RTO must be at least 1 minute")
        if self.retention_days < 1:
            raise ValueError("backup retention must be at least 1 day")
        if not self.encryption_required:
            raise ValueError("production backups must require encryption")
        if not self.restore_test_required:
            raise ValueError("production restore verification must be required")


@dataclass(frozen=True)
class BackupRecord:
    """Evidence describing one completed backup operation."""

    backup_id: str
    completed_at: str
    encrypted: bool
    integrity_verified: bool
    storage_uri: str


@dataclass(frozen=True)
class RestoreVerification:
    """Evidence that a restored database was checked before release use."""

    backup_id: str
    verified_at: str
    schema_version: int
    application_checks_passed: bool
    data_integrity_passed: bool


def _require_utc_timestamp(value: str, field_name: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    if parsed.astimezone(timezone.utc) != parsed:
        raise ValueError(f"{field_name} must use UTC")


def validate_backup_record(record: BackupRecord, policy: BackupPolicy) -> None:
    """Fail closed unless backup evidence satisfies the production policy."""
    if not record.backup_id.strip():
        raise ValueError("backup_id must be non-empty")
    _require_utc_timestamp(record.completed_at, "completed_at")
    if policy.encryption_required and not record.encrypted:
        raise RuntimeError("backup is not encrypted")
    if not record.integrity_verified:
        raise RuntimeError("backup integrity has not been verified")
    parsed = urlparse(record.storage_uri)
    if parsed.scheme not in {"https", "s3", "gs", "azure"} or not parsed.netloc:
        raise ValueError("backup storage URI must use an approved remote scheme")


def validate_restore_verification(
    verification: RestoreVerification,
    policy: BackupPolicy,
) -> None:
    """Fail closed unless restore evidence is complete and successful."""
    if not policy.restore_test_required:
        raise RuntimeError("restore verification policy is disabled")
    if not verification.backup_id.strip():
        raise ValueError("backup_id must be non-empty")
    _require_utc_timestamp(verification.verified_at, "verified_at")
    if verification.schema_version < 1:
        raise ValueError("schema_version must be at least 1")
    if not verification.application_checks_passed:
        raise RuntimeError("restored application checks did not pass")
    if not verification.data_integrity_passed:
        raise RuntimeError("restored data integrity checks did not pass")
