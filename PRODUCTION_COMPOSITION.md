# Production Composition Boundary

Production composition must use the managed persistence contract.

When `NEON_AUTH_ENV=production`, configuration validation requires a durable non-SQLite database identifier, HTTPS identity-provider and monitoring endpoints, and deployment-supplied secrets. The composition boundary must receive an injected `ManagedAuthStore` implementation.

If the managed adapter or required production configuration is unavailable, startup fails closed. The production path must never silently construct the local SQLite `AuthStore`.

Development and integration may continue using SQLite. Cloud infrastructure, credentials, production data, TLS certificates, and Apple signing or release configuration remain deployment concerns and are not committed here.


## Store account binding

The production composition root also requires an injected durable
`AccountBindingRepository`. It installs an
`AuthenticatedStoreAccountBindingService` on the composed identity service.
The binding service resolves each supplied bearer session through
`PersistentIdentityService.resolve_session`; it never accepts a client-selected
subject or binding ID. Session expiry, revocation, account blocking and trusted
device checks therefore remain in the existing authentication path.

The production composition accepts one injected DB-API connection factory and uses it for both `ManagedDbAuthStore` and `AccountBindingRepository`; the configured database pepper is used by the auth store. Set the DB-API placeholder to `%s` for PostgreSQL. The connection factory must target the validated `NEON_AUTH_DB` database. Apply production migrations 1 through 9 before serving traffic. Migration 5 creates store account bindings; migration 9 creates and seeds the singleton audit-chain head used to serialize all audit writers. The migration remains
an explicit deployment step; application startup does not silently mutate the
managed database. A production process without the durable repository fails
closed. This code does not itself create a public HTTP route or provision cloud
infrastructure.


## Authenticated HTTP endpoint

`POST /v1/store/account-binding` requires the normal `Authorization: Bearer <session>`
header. The handler validates the session through the identity service, then
asks the installed binding service for the stable server-issued identifier.
Client-supplied `subject_id` and `account_binding_id` fields are ignored.
The response contains only `account_binding_id`; no account identity is
returned. If the production binding service is not configured, the route
returns HTTP 503. Authentication failures return HTTP 401.

This endpoint is an internal app-server boundary. Deploy it behind HTTPS and
rate limiting; do not expose the development HTTP listener directly to the
public internet.
