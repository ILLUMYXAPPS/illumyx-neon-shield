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

The deployment must construct the repository with the same managed database
connection factory and the deployment-supplied database pepper, after applying
production migration 5 (`create_store_account_bindings`). The migration remains
an explicit deployment step; application startup does not silently mutate the
managed database. A production process without the durable repository fails
closed. This code does not itself create a public HTTP route or provision cloud
infrastructure.
