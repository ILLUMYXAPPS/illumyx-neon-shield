# Neon Shield Production Adapter Contract

This document defines the deployment-neutral boundary for the future production authentication adapter. It does not deploy infrastructure or select a cloud provider.

## Purpose

The local reference implementation remains development/test infrastructure only. A production adapter must provide the same server-authoritative security decisions while replacing local persistence and process-local runtime assumptions with managed production services.

## Required adapter responsibilities

The production adapter MUST:

1. Verify credentials through the approved identity provider boundary.
2. Reject blocked identities before session issuance.
3. Reject blocked phone identities before session issuance.
4. Require a trusted device before session issuance.
5. Re-check identity and device policy on session use and refresh.
6. Expire and revoke sessions server-side.
7. Rotate session identifiers on refresh.
8. Persist security events without credentials, session tokens, or raw device identifiers.
9. Preserve audit-chain integrity and support verification.
10. Fail closed when required production dependencies are unavailable or misconfigured.

## Required production dependencies

### Durable persistence

The adapter must use managed durable storage for:

- identities and account state
- trusted devices
- blocked identities
- normalized blocked phone identities
- active and revoked sessions
- security audit events
- audit-chain metadata

All database access must use parameterized queries or an ORM. Schema migrations must be versioned and repeatable.

### Secret management

Production secrets must come from the deployment platform's secret manager or equivalent runtime injection. The adapter must not contain fallback production secrets or credentials.

Required configuration categories include:

- identity-provider credentials
- database connection credentials
- session/signing secrets where applicable
- monitoring/alerting credentials
- `NEON_AUTH_ENV=production`

Missing required production secrets must stop startup or make the service unhealthy. They must never silently fall back to development values.

### TLS and network boundary

Public traffic must terminate at managed TLS infrastructure. The application service must not expose the local reference server directly to the public internet.

The production deployment must:

- accept HTTPS only at the public boundary
- reject plaintext public traffic
- use a stable production API hostname
- expose a minimal unauthenticated health endpoint containing no security state
- support automated certificate renewal

### Monitoring

The adapter must emit safe, structured events for:

- authentication failures
- rate limiting
- blocked identities
- blocked phone identities
- untrusted-device attempts
- session revocations
- unexpected authentication errors
- persistence failures
- audit-chain verification failures

Events must contain correlation-safe metadata only. Credentials, tokens, private keys, passwords, and raw device identifiers must never be logged.

## Failure behavior

Production startup MUST fail closed if any mandatory dependency or configuration is missing, including:

- production identity-provider configuration
- durable database configuration
- required session/signing secrets
- monitoring configuration where required by deployment policy

Runtime dependency failures must not cause an automatic fallback to SQLite, in-memory state, development credentials, or an alternate insecure endpoint.

## Deployment acceptance evidence

Before production release, retain evidence for:

- managed TLS and certificate renewal
- managed durable database connectivity and migration state
- secret-manager configuration without secret values in source control
- monitoring and alert delivery
- production-like authentication tests using non-production accounts
- trusted-device, blocked-identity, blocked-phone, expiry, revocation and refresh-rotation checks
- audit-event persistence and chain verification
- CI logs showing no authentication material or secrets

## Explicit non-goals

This contract does not:

- deploy a cloud provider
- create production credentials
- provision a database
- create DNS or certificates
- enable monitoring accounts
- change Apple signing, provisioning, TestFlight, or App Store configuration

Those actions require actual deployment infrastructure and credentials and must be evidenced separately.
