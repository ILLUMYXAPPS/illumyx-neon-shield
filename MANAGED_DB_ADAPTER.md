# Managed database adapter

`backend/managed_db_store.py` implements the production `ManagedAuthStore` contract. `backend/production_store_factory.py` now supplies the default PostgreSQL connection wiring for production composition.

## Integrated behavior

- Validates a PostgreSQL connection URL with an explicit TLS mode and no embedded credentials.
- Resolves database password, database pepper, and identity-provider secret through the injected `SecretProvider`.
- Supplies the separate database user and password to psycopg rather than storing credentials in the URL.
- Passes `NEON_DB_PEPPER` directly into `ManagedDbAuthStore(pepper=...)`.
- Uses DB-API `%s` placeholders and PostgreSQL `FOR UPDATE` row locking for serialized audit-chain writes.
- Applies a 10-second connection timeout and sets a recognizable application name.
- Opens connections lazily and closes them through the existing store adapter.

Install the production driver dependency with `python -m pip install -r backend/requirements-production.txt`.

## Required production configuration

- `NEON_AUTH_ENV=production`
- `NEON_AUTH_DB`: PostgreSQL URL containing host/database and an explicit `sslmode` of `require`, `verify-ca`, or `verify-full`; no embedded username/password.
- `NEON_DB_USER`: non-secret database role name with least-privilege permissions.
- `NEON_DB_PASSWORD`: database password provided by the injected secret provider.
- `NEON_DB_PEPPER`: separate high-entropy pepper provided by the injected secret provider.
- `NEON_IDP_URL`, `NEON_IDP_CLIENT_ID`, `NEON_IDP_CLIENT_SECRET`: identity-provider configuration.
- `NEON_MONITORING_ENDPOINT`: HTTPS monitoring destination. Real event and alert sink implementations must still be injected.

Prefer `sslmode=verify-full` where supported. The factory does not log connection details or secrets.

## Deployment boundaries still open

This code does **not** provision a database, create credentials, run migrations, create a connection pool, or prove a live database connection. The adapter currently opens and closes one DB-API connection per operation. Before production release, still provide a managed PostgreSQL instance, least-privilege role, versioned schema migration process, backup/restore evidence, operational monitoring, and external security review.

The production store intentionally does not fall back to SQLite. SQLite remains the development/integration implementation. Tests that use SQLite are a disposable DB-API compatibility harness, not production evidence.
