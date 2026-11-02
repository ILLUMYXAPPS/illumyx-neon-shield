# Neon Shield Production Backend Foundation

The backend now contains a dependency-free, testable boundary for server-authoritative authentication.

## Implemented

- PBKDF2-SHA256 credential records with random salts
- Optional authentication pepper from `NEON_AUTH_PEPPER`
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

SQLite is the initial persistence adapter and is **not the final managed production database**. Before public release, replace it with managed persistent infrastructure, provision the authentication pepper through a production secret store, configure HTTPS at the deployment edge, add Flutter end-to-end integration tests, and perform an external security review.

## Security rules

- Never commit credentials, tokens, signing keys, or production secrets.
- Never store raw device identifiers in audit events.
- Fail closed when device authorization cannot be established.
- Keep production configuration separate from source code.
- Every production endpoint must have automated tests before release.


## Intrusion evidence capture (opt-in integration)

The HTTP adapter accepts an injected `EvidenceStore`. When configured with
`NEON_EVIDENCE_DB`, it records server-observed failed authentication,
rate-limit, invalid-request, internal-error, and unknown-route events.
It stores only bounded request metadata and strips query strings; request
bodies, credentials, authorization headers and cookies are not captured.

Set `NEON_TRUSTED_PROXY_CIDRS` only to the exact CIDR ranges of proxies that
are directly trusted by the deployment. Forwarded-for headers from any other
peer are ignored. Never populate this setting with broad networks or values
supplied by a client.

This integration is currently an opt-in local SQLite adapter. It is not a
managed production evidence store and must not be represented as active
production capture. Public deployment requires a managed encrypted evidence
sink, verified proxy topology, retention/privacy review, access controls,
backup/restore tests and external security review. The local HTTP server still
binds to loopback and must remain behind a managed HTTPS edge.
