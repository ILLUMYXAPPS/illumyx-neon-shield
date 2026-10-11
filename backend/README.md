# Neon Shield Production Backend Foundation

The backend contains a testable boundary for server-authoritative authentication.

## Implemented

- PBKDF2-SHA256 credential records with random salts
- Optional `NEON_AUTH_PEPPER` for the SQLite development/integration adapter only
- SQLite persistence adapter for development/integration
- A DB-API managed store for PostgreSQL-compatible production persistence
- Hashed trusted-device identifiers and phone denylist
- Opaque short-lived server sessions stored as hashes
- Session rotation and server-side revocation
- Privacy-safe hash-chained audit events
- Login failure rate limiting
- JSON HTTP endpoints for health, sign-in, refresh and logout
- No request-body logging

## Production composition

When `NEON_AUTH_ENV=production`, `build_service` validates configuration and obtains required secrets through the injected `SecretProvider`. By default it constructs `ManagedDbAuthStore` through `backend.production_store_factory`, passing the database URL, separate database user/password, and `NEON_DB_PEPPER`. The PostgreSQL driver opens connections lazily with a bounded connection timeout and uses the TLS mode in the validated URL. A custom managed-store factory can be injected for a deployment-specific adapter or tests.

Install production-only driver dependencies with:

```sh
python -m pip install -r backend/requirements-production.txt
```

The production environment must supply `NEON_DB_USER` as a non-secret configuration value and resolve `NEON_DB_PASSWORD`, `NEON_DB_PEPPER`, and `NEON_IDP_CLIENT_SECRET` from the injected secret provider. `NEON_AUTH_DB` must be a PostgreSQL URL with explicit `sslmode=require`, `verify-ca`, or `verify-full`, and must not embed username/password credentials. Prefer `verify-full` where the database provider supports it.

The connection factory does not provision infrastructure, run schema migrations, or prove a live connection. Migrations must be executed as an explicit deployment step using a reviewed migration procedure. The HTTP adapter intentionally binds only to localhost. Public deployment must terminate TLS at a managed edge/reverse proxy.

## Remaining production gates

Before public release, provision a managed durable PostgreSQL database, deploy the required secrets, apply and verify versioned migrations, configure HTTPS at the deployment edge, wire real monitoring and alert delivery, test backups and restoration, add Flutter end-to-end integration tests, and complete an independent security review. None of these deployment gates is satisfied by unit tests alone.

## Secret-name contract

- `NEON_AUTH_PEPPER`: optional pepper read by the SQLite development/integration `AuthStore`; do not use it as the managed production secret.
- `NEON_DB_PEPPER`: required deployment-managed pepper for the managed database adapter.
- `NEON_DB_PASSWORD`: required database authentication secret, passed separately from the connection URL.
- `NEON_IDP_CLIENT_SECRET`: required identity-provider secret.

Secret values must never be logged or committed. Production configuration fails closed when required secrets are missing, empty, or whitespace-only.

## Security rules

- Never commit credentials, tokens, signing keys, or production secrets.
- Never store raw device identifiers in audit events.
- Fail closed when device authorization cannot be established.
- Keep production configuration separate from source code.
- Every production endpoint must have automated tests before release.
