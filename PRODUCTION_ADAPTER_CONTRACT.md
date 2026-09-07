# Neon Shield Production Adapter Contract

Deployment-neutral contract for the future managed production authentication adapter. This file does not provision infrastructure.

## Mandatory behavior

The production adapter must preserve server-authoritative credential, blocked-identity, blocked-phone, trusted-device, session expiry/revocation, refresh-rotation, audit-integrity, and safe-event behavior.

## Mandatory infrastructure

- Managed durable database for identity, trusted-device, block, session, and audit state.
- Deployment-platform secret manager for identity-provider credentials, database credentials, session/signing secrets, and monitoring configuration.
- `NEON_AUTH_ENV=production` with no development fallback.
- Managed TLS at the public boundary with HTTPS-only access, stable API hostname, health endpoint without security state, and automated renewal.
- Structured monitoring for authentication failures, rate limits, blocked identities/phones, untrusted devices, revocations, service errors, persistence failures, and audit-chain failures.

## Fail-closed rules

Missing production configuration must stop startup or make the service unhealthy. Runtime dependency failures must never fall back to SQLite, in-memory state, development credentials, or insecure endpoints.

Credentials, tokens, passwords, private keys, and raw device identifiers must never be logged.

## Acceptance evidence

Before production release, retain evidence for TLS, database connectivity/migrations, secret-manager configuration, monitoring and alert delivery, production-like authentication tests, access-control enforcement, session lifecycle behavior, audit persistence/integrity, and CI logs containing no authentication material.

## Non-goals

This contract does not provision a cloud provider, database, DNS, certificates, monitoring accounts, production credentials, or Apple signing/TestFlight/App Store configuration.
