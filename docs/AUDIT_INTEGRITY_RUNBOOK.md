# Audit-chain integrity verification runbook

## Purpose

Neon Shield audit rows are SHA-256 hash-chained. The verifier in
`backend/audit_integrity.py` checks each row's canonical event hash and the
link to the preceding row. It returns only a safe summary, not record contents.

## Implemented in the SQLite integration adapter

`AuthStore.verify_audit_integrity()` reads the complete audit table in SQLite
insertion order and verifies the returned rows. Automated tests cover both a
valid chain written through the real adapter and a tampered row detected by
that adapter method.

This adapter is for development and integration only. It is not the managed
production database implementation.

## Requirements and limits

- Read rows in authoritative insertion order, oldest first. Do not sort by a
  timestamp alone because timestamps can collide.
- Query all fields required by the verifier: `event_hash`, `event_type`,
  `occurred_at`, `subject_id`, `device_fingerprint`, and `previous_hash`.
- Production implementation must use a consistent database snapshot or the
  database's approved read/locking strategy. The SQLite method does not provide
  managed-database transaction guarantees or serialize concurrent writers.
- A valid result proves only that the supplied rows are internally consistent.
  It does not prove that rows were never deleted before the read, that the
  database itself is uncompromised, or that alert delivery works.
- Never include raw credentials, session tokens, device IDs, or full audit
  records in integrity alerts or ordinary logs.

## Verification response

- `valid=true`: all supplied rows passed linkage and content-hash checks.
- `valid=false`: fail closed, preserve the result, alert the security operator,
  and investigate using restricted access. Do not silently rewrite or delete
  evidence.
- Record verification time, database/environment identifier, row count,
  verifier version, result, and remediation reference. Avoid logging sensitive
  record contents.

## Remaining release gates

Managed-database integration, consistent snapshot/locking behaviour, scheduled
execution, alert delivery, and backup/restore verification remain release gates
until implemented and tested in the target environment.
