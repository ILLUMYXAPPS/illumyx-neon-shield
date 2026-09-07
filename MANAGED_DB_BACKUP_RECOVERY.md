# Managed Database Backup & Recovery Contract

Neon Shield treats backup and restore as explicit production deployment responsibilities. The application does not create, delete, or restore production backups automatically, and application startup must never perform a destructive restore.

## Minimum production policy

The deployment owner must configure and maintain:

- **RPO:** no more than 15 minutes of recoverable data loss.
- **RTO:** restore service within 60 minutes after a declared recovery event.
- **Retention:** keep production backups for at least 35 days, subject to legal and operational requirements.
- **Encryption:** encrypt backups in transit and at rest, with keys managed separately from the backup data.
- **Integrity:** verify each backup according to the managed provider's integrity mechanism before treating it as recovery evidence.
- **Isolation:** keep backups outside the primary database failure domain and restrict backup access using least privilege.
- **Restore testing:** perform a restore test before production release and periodically thereafter. A successful backup job alone is not proof that recovery works.

These are engineering guardrails, not evidence that the repository has provisioned managed backup infrastructure.

## Restore verification

A restore verification record should identify the backup, use an explicit UTC timestamp, record the restored schema version, and demonstrate both:

1. application-level checks passed; and
2. data-integrity checks passed.

Do not promote a restored database to production use when either class of verification fails.

The provider-neutral validation helpers in `backend/backup_policy.py` enforce these minimum evidence requirements without storing backup credentials or secret material.

## Operational recovery sequence

1. Declare the incident and freeze destructive database changes.
2. Identify the latest backup that satisfies the required RPO.
3. Verify backup integrity and encryption status.
4. Restore into an isolated recovery environment, never directly over the live database.
5. Run the versioned migration checks from `backend/migrations.py` and confirm the expected schema version.
6. Run application and data-integrity verification.
7. Record the restore verification evidence.
8. Obtain the required operational approval before redirecting production traffic.
9. Monitor authentication, database, and audit signals after recovery.
10. Preserve incident and recovery evidence for post-incident review.

## Rollback and destructive actions

The application must not automatically restore, drop, truncate, or overwrite production data at startup. Destructive recovery actions require an explicit deployment or incident-response procedure with authorization and a verified recovery point.

If a restore is unsuccessful, keep the original production database intact while the recovery environment is investigated. Never replace the known-good source solely because a restore command completed.

## Provider responsibilities

The managed database provider and deployment environment must supply the actual backup mechanism, encryption-at-rest controls, retention enforcement, access controls, restore capability, and monitoring. Those infrastructure controls must be independently verified before claiming production recovery readiness.

## Apple boundary

No Apple signing, provisioning, certificate, TestFlight, or iOS release configuration is required for this hardening step.
