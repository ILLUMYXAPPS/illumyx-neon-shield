# Production adapter verification cases

These cases are required before a managed production adapter is accepted.

- Missing `NEON_AUTH_ENV=production` must fail closed.
- Missing database configuration must fail closed.
- Missing identity-provider configuration must fail closed.
- Missing session/signing secret must fail closed.
- Missing monitoring configuration must fail closed.
- Production runtime must not fall back to SQLite or in-memory state.
- Public traffic must terminate at managed TLS.
- Authentication failures, blocked identities, blocked phones, untrusted devices, revocations, persistence failures, and audit-chain failures must produce safe monitoring events.
- Logs must contain no credentials, session tokens, passwords, private keys, or raw device identifiers.
