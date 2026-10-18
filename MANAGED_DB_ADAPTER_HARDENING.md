# Managed database adapter hardening

The managed database adapter is the production persistence seam. It remains provider-neutral.

## Safety invariants

- Production supplies the DB-API connection factory and credentials.
- The authentication pepper is deployment-supplied and mandatory.
- Identities, device identifiers and session tokens are hashed before persistence.
- SQL values use parameterized DB-API parameters.
- Connection failures roll back when supported and connections are closed.
- Audit-chain lock configuration is allowlisted to the supported empty clause or PostgreSQL-style ` FOR UPDATE`.
- SQLite is only a development/test harness, never a production fallback.

## Concurrency and operations

`add_audit_fingerprint()` serializes appends by locking the singleton `audit_chain_head` row, then inserts the event and updates that head in the same transaction. Locking a stable row also handles the empty-chain case. `migrate()` bootstraps the head for development/tests; production must add and backfill this table through a reviewed, versioned migration before deploying. PostgreSQL-style deployments should retain `audit_lock_clause=" FOR UPDATE"`.

Production releases must use versioned schema migrations, backup/restore procedures, TLS-protected connections, pooling, encryption at rest, access controls, retention and monitoring. The adapter does not provision those resources.

For production configuration, `NEON_AUTH_DB` must be a PostgreSQL connection URL with explicit TLS enabled via `sslmode=require`, `sslmode=verify-ca`, or preferably `sslmode=verify-full`. Plain PostgreSQL URLs and `sslmode=disable` are rejected before service construction.

The deployment secret name is `NEON_DB_PEPPER`.

Apple configuration remains outside this boundary.
