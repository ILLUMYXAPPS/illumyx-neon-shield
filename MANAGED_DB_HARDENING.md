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

`add_audit_fingerprint()` serializes appends by locking the singleton `audit_chain_head` row, then inserts the event and updates that head in the same transaction. This works even when the event table is empty, avoiding the gap where locking the latest event locks nothing. `migrate()` bootstraps the head from the latest existing event for test/dev use. Production rollout must add and backfill this table through a reviewed, versioned migration before deploying this code. PostgreSQL-style deployments retain `audit_lock_clause=" FOR UPDATE"`; the stable-row update itself also obtains a write lock.

## Migration boundary

The adapter's `migrate()` method is a bootstrap/test schema helper. Production releases must use versioned migrations with review, rollback procedures and backup/restore validation. Schema creation at application startup is not production migration evidence.

## Operational boundary

Production still needs a managed durable database, TLS-protected connections, pooling, backups, encryption at rest, access control, retention, failure monitoring and alerting. Those are deployment responsibilities and remain outside this provider-neutral adapter.

Apple configuration is outside this boundary and remains untouched.
