# Neon Shield Production Adapter Contract

This document defines the deployment-neutral boundary for the future production authentication adapter. It does not deploy infrastructure or select a cloud provider.

## Purpose

The local reference implementation remains development/test infrastructure only. A production adapter must preserve the server-authoritative security contract while replacing local persistence and process-local runtime assumptions with managed production services.

## Required production contract

The production adapter MUST:

- verify credentials through the approved identity-provider boundary
- reject blocked identities and blocked phone identities before session issuance
- require trusted devices before session issuance
- re-check identity and device policy on session use and refresh
- expire and revoke sessions server-side
- rotate session identifiers on refresh
- persist security events without credentials, session tokens, or raw device identifiers
- preserve audit-chain integrity and support verification
- fail closed when mandatory production dependencies are unavailable or misconfigured

## Required dependencies

### Durable persistence

Managed durable storage must persist identities, trusted devices, blocked identities, blocked phone identities, active and revoked sessions, security audit events, and audit-chain metadata.

Database access must use parameterized queries or an ORM. Schema migrations must be versioned and repeatable.

### Secret management

Production secrets must come from the deployment platform's secret manager or equivalent runtime injection. There must be no source-code fallback for production credentials.

Required runtime categories include identity-provider credentials, database credentials, session/signing secrets where applicable, monitoring configuration, and `NEON_AUTH_ENV=production`.

Missing required production configuration must stop startup or make the service unhealthy. It must never silently fall back to development values.

### TLS and network boundary

Public traffic must terminate at managed TLS infrastructure. The local reference server must not be exposed publicly.

The production boundary must use HTTPS, a stable API hostname, a minimal unauthenticated health endpoint with no security-state data, and automated certificate renewal.

### Monitoring

The adapter must emit safe structured events for authentication failures, rate limiting, blocked identities, blocked phone identities, untrusted-device attempts, session revocations, authentication-service errors, persistence failures, and audit-chain verification failures.

Credentials, tokens, private keys, passwords, and raw device identifiers must never be logged.

## Failure behavior

Production startup MUST fail closed when mandatory identity-provider configuration, durable database configuration, required session/signing secrets, or required monitoring configuration is missing.

Runtime failures must not trigger fallback to SQLite, in-memory state, development credentials, or an insecure endpoint.

## Acceptance evidence

Before production release, retain evidence for managed TLS and renewal, durable database connectivity and migrations, secret-manager configuration without secret values in source control, monitoring and alert delivery, production-like authentication tests, trusted-device and blocked-identity enforcement, session expiry/revocation/refresh rotation, audit-event persistence and chain verification, and CI logs showing no authentication material.

## Explicit non-goals

This contract does not deploy a cloud provider, create production credentials, provision a database, create DNS or certificates, enable monitoring accounts, or change Apple signing, provisioning, TestFlight, or App Store configuration.
