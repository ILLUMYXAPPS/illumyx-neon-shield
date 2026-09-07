# Managed database hardening

The managed database adapter is the production persistence seam. This change hardens the seam without selecting a cloud provider.

## Safety invariants

- Production supplies the DB-API connection factory and credentials.
- The authentication pepper is deployment-supplied and mandatory.
- Authentication identities, device identifiers and session tokens are hashed before persistence.
- SQL values use parameterized DB-API parameters.
- Connection failures roll back when supported and always close the connection.
- Audit-chain lock configuration is allowlisted to the supported empty clause or PostgreSQL-style ` FOR UPDATE`; arbitrary SQL cannot be injected through deployment configuration.
- SQLite remains a disposable test harness and development adapter, not production infrastructure.

## Audit-chain concurrency

`add_audit_fingerprint()` reads the latest audit hash and writes the next event in one transaction. A production deployment with concurrent writers must use a database transaction/row-lock strategy that serializes that read/write sequence. PostgreSQL-style deployments should provide `audit_lock_clause=" FOR UPDATE"` together with an appropriate transaction isolation level.

## Migration boundary

The adapter's `migrate()` method is a bootstrap/test schema helper. Production releases must use versioned migrations with review, rollback procedures and backup/restore validation. Schema creation at application startup is not production migration evidence.

## Operational boundary

Production still needs a managed durable database, TLS-protected connections, pooling, backups, encryption at rest, access control, retention, failure monitoring and alerting. Those are deployment responsibilities and remain outside this provider-neutral adapter.

Apple configuration is outside this boundary and remains untouched.
