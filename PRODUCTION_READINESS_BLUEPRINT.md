# Neon Shield Production Readiness Blueprint

## Purpose

This document defines the evidence-driven path from application hardening to production-like validation and release. It does not claim infrastructure is provisioned and does not replace Apple certification or store review.

## Phase 1: Production architecture

Required deployment components:

- HTTPS/TLS termination with certificate renewal monitoring
- Managed PostgreSQL with explicit TLS
- Connection pooling and bounded database timeouts
- Deployment-managed secret provider
- Server-authoritative authentication/session service
- Security event sink
- Security alert sink
- Versioned deployment-time database migrations
- Managed backup/recovery meeting the documented RPO/RTO/retention policy
- Rate limiting and abuse controls
- Centralized logs with sensitive-value exclusion

Production must fail closed if a required dependency is absent.

## Phase 2: Production-like environment

Use disposable non-production infrastructure with production-equivalent boundaries but test-only credentials/data.

Minimum evidence:

1. Application starts with all required dependencies injected.
2. Missing managed DB, secret provider, event sink or alert sink prevents production startup.
3. HTTPS is enforced.
4. PostgreSQL TLS validation succeeds.
5. Deployment migrations run separately from application startup.
6. Backup evidence and a non-destructive restore verification are recorded.

## Phase 3: Authentication validation

Exercise the complete server-authoritative lifecycle:

- owner/account setup
- successful authentication
- failed authentication
- rate limiting
- trusted-device enrollment
- trusted-device rejection
- session issuance
- session expiry
- session revocation
- refresh rotation
- concurrent refresh attempts
- blocked identity
- blocked phone
- audit event creation
- warning/critical alert routing

For concurrent refresh, prove that one old session can be consumed only once.

## Phase 4: Recovery and identity verification

No production-ready recovery or identity-verification claim is made until the actual integration is present and independently reviewed.

Required evidence when implemented:

- recovery token confidentiality
- single use
- expiration
- replay rejection
- rate limiting
- account-enumeration resistance
- identity-verification failure handling
- audit coverage
- independent review and retest

## Phase 5: Mobile real-device validation

For each supported release device:

1. Install the candidate build.
2. Verify onboarding and authentication.
3. Establish trusted-device state.
4. Verify protected operations.
5. Revoke/remove the device.
6. Confirm subsequent protected access is rejected.
7. Exercise re-enrollment/recovery.
8. Repeat critical checks after update/reinstall where applicable.
9. Record device model, OS, app version, date, result and evidence.

## Phase 6: Apple release path

Apple work is intentionally deferred until the application and production-like evidence is ready.

Required release evidence:

- Apple Developer account in good standing
- distribution certificates
- provisioning profiles
- signing validation
- archive validation
- TestFlight upload and install verification
- App Store metadata
- privacy/support declarations
- production configuration review
- submission evidence
- Apple review decision

Apple approval cannot be guaranteed by this project checklist.

## Release evidence rule

Do not increase the readiness percentage because a task was attempted. Increase it only after a meaningful gate has evidence.

Application security and production infrastructure are separate dimensions. A fully hardened codebase is not equivalent to a deployed production system.

## Current boundary

Application-level hardening is substantially complete. Remaining work is evidence collection, deployment validation, real-device validation, Apple signing/release work and final external review.
