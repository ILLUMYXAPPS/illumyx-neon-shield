# Production Composition Boundary

Neon Shield has an explicit separation between local development and production composition.

## Production

When `NEON_AUTH_ENV=production`, `backend.composition.build_service()`:

1. validates required production configuration;
2. rejects local SQLite-style database URLs;
3. requires HTTPS identity-provider and monitoring endpoints; and
4. requires an injected `ManagedAuthStore` implementation.

If the managed adapter is absent, startup fails closed. The production path never silently constructs the local SQLite `AuthStore`.

## Development and integration

When production mode is not enabled, the existing SQLite `AuthStore` remains available for local development and integration tests.

## Deployment responsibility

A deployment composition root must create the managed durable database adapter and inject it into `build_service(managed_store=...)`. Database credentials, identity-provider credentials, session secrets, monitoring credentials, TLS certificates and production endpoints belong in the deployment platform's secret/configuration system, not this repository.

This change does not provision a cloud database, create credentials, select a cloud provider, or configure Apple signing, provisioning, TestFlight or the App Store.
