# Managed database migration contract

Production schema changes use `backend.migrations.MigrationRunner` as an explicit deployment step. The application startup path does not run migrations automatically.

## Safety contract

- Migration versions start at `1` and are contiguous.
- Versions are unique and migration names must remain stable after release.
- The runner records applied versions in `neon_schema_migrations`.
- Unknown database versions fail closed.
- Missing or non-contiguous migration history fails closed.
- Pending migrations execute in order inside one explicit DB-API transaction and roll back on failure when the driver supports transactional DDL.
- The runner accepts the same DB-API placeholders used by the managed store: `?`, `%s`, or `:1`.
- Migration definitions are code-reviewed and shipped with the release.

## Operational boundary

Production deployment automation must run migrations before starting application instances that require the new schema. Destructive or irreversible migrations require a reviewed backup/restore plan and explicit deployment approval.

The existing `ManagedDbAuthStore.migrate()` method remains a bootstrap/test schema helper. It is not production migration evidence and must not be invoked automatically during application startup.

A real production database, backup service, restore validation, connection pooling, TLS, credentials, encryption at rest, access controls and monitoring remain deployment responsibilities.

Apple signing and release configuration remain outside this boundary.
