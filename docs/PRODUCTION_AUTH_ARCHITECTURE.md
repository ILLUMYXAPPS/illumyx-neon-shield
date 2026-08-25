# Neon Shield Production Authentication Architecture

## Purpose

Define the production boundary required before Neon Shield moves from beta to a stable security release.

## Boundary

The Flutter and desktop clients are untrusted clients. Authentication and authorization decisions must be made by a server-side identity service.

The service must provide:

- short-lived server-issued sessions
- server-side session revocation
- trusted-device registration and revocation
- blocked-identity enforcement
- security-event audit records
- rate limiting and abuse protection
- HTTPS-only transport
- managed persistent storage
- secrets stored outside source control

## Client rules

Clients must never treat a locally stored flag, device identifier, or client-generated token as proof of authentication.

The client may cache presentation state, but every protected operation must be authorized by a valid server-issued session.

## Deployment gates

Before prerelease approval, the implementation must demonstrate:

1. HTTPS transport in the deployed environment.
2. Production secrets supplied through the hosting platform's secret store.
3. Persistent storage with backups and access controls.
4. Authentication rate limits and lockout/abuse controls.
5. Security-event monitoring and alerting.
6. Mobile integration using server-issued sessions.
7. Automated tests for login, expiry, revocation, device trust, blocked identities, and abuse controls.
8. Independent security review of the production configuration.

This document is an architecture gate only. It does not claim that production authentication is deployed.
