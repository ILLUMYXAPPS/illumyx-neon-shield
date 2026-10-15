"""Fail-closed verification for Neon Shield's hash-chained audit records.

Callers must provide records in authoritative insertion order (oldest first).
This verifier is intentionally read-only and does not claim to provide database
locking, tamper-proof storage, or an operational scheduler by itself.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

GENESIS_HASH = "0" * 64
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FIELDS = (
    "event_hash",
    "event_type",
    "occurred_at",
    "subject_id",
    "device_fingerprint",
    "previous_hash",
)


@dataclass(frozen=True)
class AuditIntegrityResult:
    """Safe summary of an audit-chain verification attempt."""

    valid: bool
    event_count: int
    invalid_index: int | None = None
    reason: str | None = None


def _canonical_hash(record: Mapping[str, Any]) -> str:
    # Keep this serialization aligned with AuthStore.add_audit_fingerprint.
    payload = (
        f"{record['event_type']}|{record['occurred_at']}|"
        f"{record['subject_id'] or ''}|{record['device_fingerprint']}|"
        f"{record['previous_hash']}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_audit_chain(records: Iterable[Mapping[str, Any]]) -> AuditIntegrityResult:
    """Verify linkage and content hashes without exposing record contents.

    Supports ordinary mappings and row objects exposing a keys() method (for
    example sqlite3.Row). The first record must link to GENESIS_HASH. Every
    subsequent record must link to the preceding event_hash, and its own hash
    must match the canonical fields. A malformed record fails closed.
    """
    previous_hash = GENESIS_HASH
    count = 0

    try:
        for index, source_record in enumerate(records):
            if isinstance(source_record, Mapping):
                record = source_record
            elif callable(getattr(source_record, "keys", None)):
                record = dict(source_record)
            else:
                return AuditIntegrityResult(False, count, index, "malformed_record")

            if any(field not in record for field in _REQUIRED_FIELDS):
                return AuditIntegrityResult(False, count, index, "missing_field")

            if not all(
                isinstance(record[field], str)
                for field in (
                    "event_hash",
                    "event_type",
                    "occurred_at",
                    "device_fingerprint",
                    "previous_hash",
                )
            ):
                return AuditIntegrityResult(False, count, index, "invalid_field_type")

            if record["subject_id"] is not None and not isinstance(record["subject_id"], str):
                return AuditIntegrityResult(False, count, index, "invalid_field_type")

            if not _SHA256_HEX.fullmatch(record["event_hash"]):
                return AuditIntegrityResult(False, count, index, "malformed_event_hash")
            if not _SHA256_HEX.fullmatch(record["previous_hash"]):
                return AuditIntegrityResult(False, count, index, "malformed_previous_hash")

            if not hmac.compare_digest(record["previous_hash"], previous_hash):
                return AuditIntegrityResult(False, count, index, "chain_link_mismatch")

            expected_hash = _canonical_hash(record)
            if not hmac.compare_digest(record["event_hash"], expected_hash):
                return AuditIntegrityResult(False, count, index, "event_hash_mismatch")

            previous_hash = record["event_hash"]
            count += 1
    except (KeyError, TypeError, ValueError, UnicodeError):
        return AuditIntegrityResult(False, count, count, "malformed_record")

    return AuditIntegrityResult(True, count)
