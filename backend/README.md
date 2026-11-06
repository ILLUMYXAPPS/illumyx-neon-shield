# Neon Shield Production Backend Foundation

The backend contains a dependency-free, testable boundary for server-authoritative authentication.

## Implemented

- PBKDF2-SHA256 credential records with random salts
- Optional `NEON_AUTH_PEPPER` for the SQLite development/integration adapter only
- SQLite persistence adapter for development/integration
- Hashed trusted-device identifiers and phone denylist
- Opaque short-lived server sessions stored as hashes
- Session rotation and server-side revocation
- Privacy-safe hash-chained audit events
- Login failure rate limiting
- JSON HTTP endpoints for health, sign-in, refresh and logout
- No request-body logging

## Endpoints

- `GET /health`
- `POST /v1/auth/sign-in`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`

The HTTP adapter intentionally binds only to localhost. Public deployment must terminate TLS at a managed edge/reverse proxy and keep secrets outside source control.

## Production gate still required

SQLite is the initial persistence adapter and is **not the final managed production database**. Before public release, replace it with managed persistent infrastructure, provision required production secrets through the injected deployment secret provider, configure HTTPS at the deployment edge, add Flutter end-to-end integration tests, and perform an external security review.

## Secret-name contract

- `NEON_AUTH_PEPPER`: optional pepper read by the SQLite development/integration `AuthStore`; do not treat this as the managed production secret name.
- `NEON_DB_PEPPER`: required deployment-managed pepper for the managed database adapter. Production configuration obtains it through the injected `SecretProvider`.
- `NEON_IDP_CLIENT_SECRET`: required identity-provider secret, also obtained only through the injected `SecretProvider`.

Production configuration fails closed when either required secret is missing, empty, or whitespace-only. Do not add a session secret without a concrete, tested cryptographic consumer.

## Security rules

- Never commit credentials, tokens, signing keys, or production secrets.
- Never store raw device identifiers in audit events.
- Fail closed when device authorization cannot be established.
- Keep production configuration separate from source code.
- Every production endpoint must have automated tests before release.
