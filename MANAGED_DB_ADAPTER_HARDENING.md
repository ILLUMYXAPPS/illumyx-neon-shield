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

`add_audit_fingerprint()` reads the latest audit hash and writes the next event in one transaction. Concurrent production writers require a database transaction/row-lock strategy that serializes this sequence. PostgreSQL-style deployments should supply `audit_lock_clause=" FOR UPDATE"` with suitable transaction isolation.

Production releases must use versioned schema migrations, backup/restore procedures, TLS-protected connections, pooling, encryption at rest, access controls, retention and monitoring. The adapter does not provision those resources.

The deployment secret name is `NEON_DB_PEPPER`.

Apple configuration remains outside this boundary.
