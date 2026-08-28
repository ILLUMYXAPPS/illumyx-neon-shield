# Neon Shield Production Backend Foundation

This directory is the production-backend boundary for Neon Shield.

The initial foundation is intentionally documentation-only until the API contract, persistence choice, deployment target, and secret-management mechanism are explicitly selected and implemented with tests.

## Required production components

- Authentication and account lifecycle
- Server-authoritative trusted-device enforcement
- Session issuance, refresh, rotation, and revocation
- Privacy-safe audit events
- Persistent storage
- HTTPS deployment
- Production secret management
- Integration tests from the Flutter client

## Security rules

- Never commit credentials, tokens, signing keys, or production secrets.
- Do not store raw device identifiers in audit events.
- Fail closed when device authorization cannot be established.
- Keep production configuration separate from source code.
- Every production endpoint must have automated tests before release.

This file establishes the backend boundary without inventing an unverified framework or deployment provider.