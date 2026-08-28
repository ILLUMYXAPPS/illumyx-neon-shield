# Neon Shield Production Deployment Gate

This document is the release checklist for moving the reference authentication service to production infrastructure without weakening the existing security contract.

## Non-negotiable security boundary

The production adapter must preserve the `auth_server_contract.py` boundary and the existing server-authoritative decisions:

1. Verify credentials on the server.
2. Reject blocked identities before issuing a session.
3. Reject blocked phone identities before issuing a session.
4. Require the device to be trusted before issuing a session.
5. Re-check identity and device policy on session use/refresh.
6. Expire and revoke sessions server-side.
7. Rotate session identifiers on refresh.
8. Record security events without credentials, tokens, or raw device identifiers.

`auth_server.py` remains an in-process reference implementation. It must not be exposed as the production authentication service.

## Production infrastructure gates

### 1. HTTPS-only API

- [ ] Deploy the production API behind managed TLS.
- [ ] Redirect or reject plaintext HTTP.
- [ ] Configure a stable production API base URL for mobile clients.
- [ ] Add a health endpoint that exposes no authentication or security-state data.
- [ ] Verify certificate validity and automated renewal.

### 2. Managed persistence

Production state must not depend on process memory.

Persist at minimum:

- account/identity records
- credential-verification metadata handled by the identity provider
- trusted devices
- blocked identities
- normalized blocked phone identities
- active/revoked sessions
- security audit events
- audit-chain metadata required for integrity verification

Use parameterized queries or an ORM. Do not log credentials, session tokens, or raw device identifiers.

### 3. Secrets

Secrets must be supplied by the deployment platform's secret manager/environment configuration.

Required secret/configuration categories:

- production identity-provider credentials
- database connection credentials
- session/signing secrets where applicable
- monitoring/alerting credentials
- application environment (`production`)

Never commit secret values, generated credentials, certificates, private keys, or production database dumps to Git.

### 4. Monitoring and alerting

Monitor at minimum:

- authentication failures
- rate-limit events
- blocked identity attempts
- blocked phone attempts
- untrusted-device attempts
- session revocations
- unexpected authentication-service errors
- database connectivity failures
- audit-chain verification failures

Alerts should identify the event category and safe correlation information without exposing credentials, tokens, or raw device IDs.

### 5. Production verification

Before beta/release:

- [ ] Run the full Python test matrix.
- [ ] Run Flutter analysis and tests.
- [ ] Run Android release build.
- [ ] Run iOS release build/signing validation.
- [ ] Exercise production authentication against a non-production test account.
- [ ] Verify trusted-device removal immediately prevents subsequent session use/refresh.
- [ ] Verify blocked identity and blocked phone enforcement.
- [ ] Verify session expiry, revocation and refresh rotation.
- [ ] Verify security events are persisted and chain integrity can be checked.
- [ ] Verify no secrets or authentication material appear in CI logs.

## Release rule

Do not mark this gate complete because CI is green alone. Production HTTPS, managed persistence, secret management, monitoring, and independent identity/security review require deployment evidence.

## Current state

Application-side authentication and access-control tests are passing in CI. Production infrastructure remains a release prerequisite.
