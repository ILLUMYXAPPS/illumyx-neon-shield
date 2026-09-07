# Independent Identity & Authentication Security Review

## Scope

This review covers the server-authoritative authentication/session boundary, trusted-device enforcement, blocked identities/phones, session lifecycle, credential handling, rate limiting, security telemetry, and production composition.

## Findings

### AUTH-01: Refresh-token rotation must be atomic

**Severity:** High

The authentication service previously loaded a valid session, revoked it, and then inserted the replacement session as separate persistence operations. Two concurrent refresh requests could both observe the original session as valid and both issue replacement sessions. GitHub's status checks validate repository changes, but they do not provide a substitute for application-level concurrency guarantees. citeturn0search0

**Remediation:** add an adapter-level atomic `rotate_session()` operation. The old session is consumed and the replacement session is created in one database transaction. Only one concurrent refresh can succeed.

### AUTH-02: Production checks must remain deployment evidence, not code-only claims

The release gate correctly leaves production-like blocked-identity, session lifecycle, and real-device checks unverified until they are actually executed. This review does not mark those deployment checks complete.

### AUTH-03: Production authentication has the correct fail-closed dependency boundary

The service consumes `ManagedAuthStore`, and production composition requires deployment-supplied persistence/secrets/observability dependencies. No SQLite fallback is claimed as production infrastructure.

## Verified controls

- credentials are stored as PBKDF2-derived records rather than plaintext
- identity and device identifiers are hashed at persistence/telemetry boundaries
- blocked identity and phone checks occur before session issuance
- trusted-device enforcement occurs before session issuance
- active sessions re-check identity and device policy
- sessions have bounded TTLs
- session refresh rotates the credential
- revoked/expired sessions are rejected
- rate limiting is bounded and fail-closed
- security telemetry uses allowlisted metadata and hashed identifiers
- monitoring/alert delivery failures are not silently swallowed
- production composition requires explicit infrastructure boundaries

## Residual verification

Production-like end-to-end verification, managed database deployment, secret-management integration, real monitoring delivery, and real-device smoke tests remain deployment/release evidence items. They are not marked complete by this code review.

## Apple boundary

No Apple signing, provisioning, certificate, TestFlight, or iOS release configuration is part of this review.
