# Neon Shield Production Authentication Architecture

## Purpose

Define the production boundary required before Neon Shield moves from beta to a stable security release.

## Boundary

The Flutter and desktop clients are untrusted clients. Authentication and authorization decisions must be made by a server-side identity service.

The repository reference implementation in `auth_server.py` demonstrates this policy boundary without claiming to be a production network service. A production adapter must supply managed persistence, credential verification, HTTPS transport, secret storage, and operational monitoring.

The service must provide:

- short-lived server-issued sessions
- server-side session revocation
- trusted-device registration and revocation
- blocked-identity enforcement
- phone denylist enforcement where phone identity is part of authorization
- security-event audit records
- rate limiting and abuse protection
- HTTPS-only transport
- managed persistent storage
- secrets stored outside source control

## Authoritative decision order

For sign-in, the server must first authenticate the owner/account. It must then enforce blocked identity and phone policy, followed by recognised-device membership, before issuing a session.

A client-provided trusted flag, locally cached decision, or client-generated token is never sufficient to grant access.

## Client rules

Clients must never treat a locally stored flag, device identifier, or client-generated token as proof of authentication.

The client may cache presentation state, but every protected operation must be authorized by a valid server-issued session.

## Audit and privacy rules

Security events must not contain credentials, authentication tokens, raw phone numbers, or raw device identifiers. Device identifiers used for security correlation should be represented by a non-reversible fingerprint or an equivalent protected identifier in audit storage.

The reference implementation uses a hash-chained audit record so tampering with event ordering or contents is detectable. Production deployments must provide durable, access-controlled and independently monitored audit storage.

## Local-first beta fallback

If the backend is unavailable, the local-first beta may continue to display locally available defensive posture information, but it must not represent the user as having a newly server-authenticated session. Production-protected operations must fail closed when a valid server-issued session cannot be established or refreshed.

## Deployment gates

Before prerelease approval, the implementation must demonstrate:

1. HTTPS transport in the deployed environment.
2. Production secrets supplied through the hosting platform's secret store.
3. Persistent storage with backups and access controls.
4. Authentication rate limits and lockout/abuse controls.
5. Security-event monitoring and alerting.
6. Mobile integration using server-issued sessions.
7. Automated tests for login, expiry, revocation, device trust, blocked identities, phone policy, and abuse controls.
8. Independent security review of the production configuration.

This document is an architecture gate only. It does not claim that production authentication is deployed.
