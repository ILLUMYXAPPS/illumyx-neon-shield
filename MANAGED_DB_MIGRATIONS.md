# Managed database migration contract

Production schema changes use `backend.migrations.MigrationRunner` as an explicit deployment step. The application startup path does not run migrations automatically.

## Safety contract

- Migration versions start at `1` and are contiguous.
- Versions are unique and migration names must remain stable after release.
- The runner records applied versions in `neon_schema_migrations`.
- Unknown database versions fail closed.
- Missing or non-contiguous migration history fails closed.
- Pending migrations execute in order inside one explicit DB-API transaction and roll back on failure when the driver supports transactional DDL.
- SQLite uses `BEGIN IMMEDIATE` to serialize writers before migration history is read. PostgreSQL deployment commands acquire a transaction-scoped advisory lock before reading or changing migration history.
- The runner accepts the same DB-API placeholders used by the managed store: `?`, `%s`, or `:1`.
- Migration definitions are code-reviewed and shipped with the release.
- Migration `4`, `create_serialized_audit_chain_head`, creates the singleton audit-chain head using the canonical `event_hash` column and derives its value from the actual `previous_hash` links, not timestamps. Existing heads are validated before the migration is recorded as applied. Forked, disconnected, orphaned, cyclic, stale, or otherwise ambiguous history fails closed.

## Operational boundary

Production deployment automation must run migrations before starting application instances that require the new schema. Destructive or irreversible migrations require a reviewed backup/restore plan and explicit deployment approval.

The existing `ManagedDbAuthStore.migrate()` method remains a bootstrap/test schema helper. It is not production migration evidence and must not be invoked automatically during application startup. The managed store and production migration both use `audit_chain_head.event_hash`; do not introduce a competing `last_event_hash` column without a separately reviewed schema migration.

A real production database, backup service, restore validation, connection pooling, TLS, credentials, encryption at rest, access controls and monitoring remain deployment responsibilities.

Apple signing and release configuration remain outside this boundary.
