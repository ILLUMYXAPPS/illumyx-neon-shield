# Managed DB audit notes

The adapter uses a deployment-supplied DB-API connection factory and pepper. It does not select a provider or fall back to SQLite.

Security review points:

- Parameterized values are used for application data queries.
- Authentication identities, device identifiers and session tokens are hashed before persistence.
- Credential records use the existing password-hashing implementation.
- Connection exceptions roll back when the driver exposes rollback and always close the connection.
- Audit-chain writes are transactional and support a PostgreSQL-style ` FOR UPDATE` deployment lock.
- The audit lock clause is allowlisted to prevent arbitrary SQL from entering deployment configuration.
- Production schema changes require versioned migrations, not application-startup schema creation.
- Production requires TLS, pooling, backups, encryption at rest, access controls and monitoring supplied by infrastructure.

The production secret used by the adapter is `NEON_DB_PEPPER`.
