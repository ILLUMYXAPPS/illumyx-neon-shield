# Neon Shield Security Review 71

## Scope
Application-level review after PR #70. Apple signing, provisioning, TestFlight, certificates and production infrastructure remain out of scope.

## Findings

### Recovery / identity boundary
No password-reset, recovery-token, OTP, or identity-verification implementation was found in the current repository search. This is therefore a deployment/integration gate rather than a code path that can be safely marked implemented.

### Session security
The server-authoritative service validates session tokens, expiry, blocked identities and trusted-device state before refresh. Refresh rotation is atomic through the persistence contract, and PR #70 makes managed-database row locking the default for the relevant concurrency-sensitive queries.

### Production composition
Production requires an injected secret provider, managed persistence store, security-event sink and security-alert sink. Production configuration requires PostgreSQL and explicit TLS plus HTTPS identity-provider and monitoring endpoints. No development persistence fallback is permitted when production mode is active.

### Secrets
The repository does not contain production secret values. The current production secret contract requires `NEON_IDP_CLIENT_SECRET` and `NEON_DB_PEPPER` through the injected secret provider. `NEON_SESSION_SECRET` is intentionally not part of that contract because the current session design uses opaque random server-side tokens and has no separate session-signing or encryption consumer. Do not provision it unless a concrete, tested cryptographic use is introduced and reviewed.

### Audit trail
Audit records are chained by SHA-256 hashes. Managed DB audit reads use the production-safe row-locking default introduced by PR #70. Production deployment still needs a database-level verification strategy for concurrent writers and an operational integrity-check procedure.

### Monitoring
Security telemetry is validated and routed through provider-neutral event and alert boundaries. Warning and critical events require an injected alert sink. Actual alert destination, credentials and delivery infrastructure remain deployment responsibilities.

### Repository sweep
No private-key material, password-reset implementation, recovery-token implementation, or unsafe plaintext production HTTP path was identified by the focused repository searches performed in this review.

## Decision
Application-level security hardening remains strong, but production readiness must not be marked complete until deployment evidence exists for HTTPS, managed persistence, production secrets, monitoring/alert delivery, identity verification/recovery integration, real-device validation and Apple signing/release gates.
