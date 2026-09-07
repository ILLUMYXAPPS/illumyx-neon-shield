# Production Secret Boundary

Neon Shield production code consumes deployment secrets through `SecretProvider` rather than reading provider-specific secret stores directly.

## Required production secrets

- `NEON_IDP_CLIENT_SECRET`
- `NEON_DB_PEPPER`

`PersistentIdentityService` uses opaque, random server-side session tokens that are persisted as hashes and rotated atomically. There is currently no cryptographic consumer for a separate session-signing/encryption secret, so `NEON_SESSION_SECRET` is intentionally not part of the production contract.

Database credentials are deployment-managed as part of `NEON_AUTH_DB`; the application does not provide credential defaults.

## Rules

- Missing or empty required secrets fail closed.
- Secret values are never emitted through observability events or error messages.
- The application does not generate production fallback secrets.
- `EnvironmentSecretProvider` is a provider-neutral deployment adapter, not a cloud-vendor commitment.
- A managed secret-store implementation can replace it without changing authentication code.
- Apple configuration remains outside this boundary.
