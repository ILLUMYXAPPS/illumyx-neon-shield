# Audit-chain integrity verification runbook

## Purpose

Neon Shield audit rows are SHA-256 hash-chained. The verifier in
`backend/audit_integrity.py` checks each row's canonical event hash and the
link to the preceding row. It returns only a safe summary, not record contents.

## Requirements and limits

- Read rows in authoritative insertion order, oldest first. Do not sort by a
  timestamp alone because timestamps can collide.
- Query all fields required by the verifier: `event_hash`, `event_type`,
  `occurred_at`, `subject_id`, `device_fingerprint`, and `previous_hash`.
- Run against a consistent database snapshot or under the database's approved
  read/locking strategy. This module does not create that snapshot or serialize
  concurrent writers.
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

## Deployment status

This verifier is a read-only building block. Production wiring, consistent
snapshot/locking behaviour, scheduled execution, alert delivery, and backup/
restore verification remain separate release gates until implemented and
tested in the target environment.
