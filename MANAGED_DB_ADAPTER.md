# Managed database adapter

`backend/managed_db_store.py` is the first concrete implementation behind `ManagedAuthStore`.

## What it does

- persists users, trusted devices, blocked phones, sessions and audit-chain events in a durable SQL database;
- hashes identities, device identifiers and session tokens before persistence;
- hashes credentials with the existing PBKDF2 implementation;
- fails closed when the deployment-supplied authentication pepper is missing;
- accepts an injected DB-API connection factory, so the application does not select a cloud provider or embed credentials;
- supports DB-API placeholder styles used by common drivers;
- allows a deployment-specific row-lock clause for serialized audit-chain writes.

## Production requirements

This adapter does **not** provision a database or credentials. A production deployment must provide:

1. a managed durable database;
2. TLS-protected database connections;
3. a connection pool or equivalent safe connection lifecycle;
4. credentials and `NEON_AUTH_PEPPER` from a deployment secret manager;
5. versioned schema migrations and rollback procedures;
6. backups, encryption at rest, retention and access controls;
7. a transaction/row-lock strategy that serializes audit-chain writes. PostgreSQL-style deployments should supply `audit_lock_clause=" FOR UPDATE"`;
8. monitoring and alerting for connection failures, transaction failures and authentication-store errors.

The adapter intentionally has no production fallback to SQLite. The existing SQLite `AuthStore` remains the development/integration implementation. Production composition must continue to inject `ManagedDbAuthStore` or another `ManagedAuthStore` implementation.

## Provider neutrality

No cloud provider is selected by this change. The connection factory is the deployment seam. A later infrastructure change can supply a managed PostgreSQL-compatible driver, another supported DB-API implementation, or a platform-specific adapter without changing `PersistentIdentityService`.

## Validation boundary

The included tests use SQLite only as a disposable test harness for the adapter's DB-API behavior. They do not represent production infrastructure and must not be interpreted as production deployment evidence.
