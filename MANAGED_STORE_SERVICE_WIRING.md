# Managed Store Service Wiring

The server-authoritative `PersistentIdentityService` now depends on the `ManagedAuthStore` production persistence contract rather than the concrete SQLite `AuthStore`.

## Boundary

- `ManagedAuthStore` is the dependency-injection boundary for production persistence.
- `PersistentIdentityService` consumes that boundary for identities, trusted devices, blocked identities/phones, sessions, revocation and audit events.
- The existing SQLite `AuthStore` remains the development/integration adapter and is not a production deployment.
- No cloud provider, database credentials, production endpoint, or production data is introduced by this change.

## Production rule

A production composition root must construct `PersistentIdentityService` with a managed durable implementation of `ManagedAuthStore`. If that implementation or required production configuration is unavailable, deployment must fail closed rather than silently falling back to SQLite.

## Compatibility

Authentication policy remains in `PersistentIdentityService`; storage policy remains behind the adapter contract. This keeps server-authoritative decisions in one service while allowing the production database implementation to change independently.

Apple signing, provisioning, TestFlight and App Store configuration are outside this boundary.
