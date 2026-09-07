# Neon Shield Production Security Runbook

This runbook defines the production hardening boundary before any public service or stable release. It does not provision infrastructure and must not be treated as evidence that infrastructure has been deployed.

## Security invariants

The production adapter must preserve the server-authoritative authentication contract:

- Credentials are verified server-side.
- Blocked identities and blocked phone identities are rejected before session issuance.
- A device must be trusted before session issuance.
- Identity and device policy are re-checked on session use and refresh.
- Sessions expire and revoke server-side.
- Refresh rotates the session identifier and invalidates the previous session.
- Security events contain safe correlation data only. Never store credentials, bearer tokens, or raw device identifiers in logs.

## Required production components

### 1. TLS and API edge

- [ ] Managed TLS is enabled.
- [ ] Plain HTTP is rejected or redirected at the edge.
- [ ] HSTS is enabled after HTTPS-only operation is verified.
- [ ] Production API has a stable hostname.
- [ ] Health endpoint returns only service-health information.
- [ ] Certificate renewal is automated and monitored.
- [ ] Database and administrative ports are not publicly exposed.

### 2. Durable persistence

Use a managed production database rather than process memory.

Minimum durable state:

- identities and identity-provider references
- trusted devices
- blocked identities
- normalized blocked phone identities
- active and revoked sessions
- security audit events
- audit-chain metadata

Database requirements:

- [ ] Encryption at rest provided by the managed service.
- [ ] TLS required for application-to-database connections.
- [ ] Least-privilege application database account.
- [ ] Parameterized queries or a maintained ORM only.
- [ ] Automated backups enabled.
- [ ] Restore procedure tested before release.
- [ ] Retention policy documented.

### 3. Secret management

Production secrets must exist only in the deployment platform's secret manager or equivalent secure environment configuration.

Required categories:

- identity-provider credentials
- database credentials
- session/signing secrets where applicable
- monitoring/alerting credentials
- production environment configuration

Rules:

- [ ] No production secret committed to Git.
- [ ] No production secret stored in application source.
- [ ] No private signing key generated or uploaded by CI.
- [ ] Secrets are masked in deployment logs.
- [ ] Rotation procedure documented.
- [ ] Access to production secrets is least-privilege.

### 4. Monitoring and alerting

Collect security telemetry with safe correlation identifiers.

Monitor:

- authentication failures
- rate-limit events
- blocked identity attempts
- blocked phone attempts
- untrusted-device attempts
- session revocations
- unexpected authentication-service errors
- database connectivity failures
- audit-chain verification failures

Alert on sustained or unusual patterns. Alerts must never contain passwords, bearer tokens, private keys, or raw device identifiers.

### 5. Production-like verification

Use a dedicated non-production test account and test devices. Never use a real user's credentials for validation.

Verify:

- [ ] Successful authentication issues a server session.
- [ ] Blocked identity cannot obtain a session.
- [ ] Blocked phone identity cannot obtain a session.
- [ ] Untrusted device cannot obtain a session.
- [ ] Removing trust prevents subsequent session use/refresh.
- [ ] Revoked sessions cannot be reused.
- [ ] Expired sessions cannot be reused.
- [ ] Refresh rotates the session identifier.
- [ ] Security events are persisted.
- [ ] Audit-chain integrity can be verified after persistence/restart.
- [ ] CI/deployment logs contain no authentication material.

## Release evidence

A production gate is green only when evidence exists for each infrastructure item. Passing application CI alone is insufficient.

Record for each gate:

- date/time verified
- environment name
- test account identifier (non-sensitive reference only)
- result
- evidence location
- reviewer

Do not place credentials, tokens, private keys, database dumps, or raw device identifiers in the evidence record.

## Apple boundary

This runbook intentionally excludes Apple Developer enrollment, certificates, provisioning profiles, signing, TestFlight, and App Store release configuration. Those remain a later phase.
