# Production Composition Boundary

Production composition must use the managed persistence contract.

When `NEON_AUTH_ENV=production`, configuration validation requires a durable non-SQLite database identifier, HTTPS identity-provider and monitoring endpoints, and deployment-supplied secrets. The composition boundary must receive an injected `ManagedAuthStore` implementation.

If the managed adapter or required production configuration is unavailable, startup fails closed. The production path must never silently construct the local SQLite `AuthStore`.

Development and integration may continue using SQLite. Cloud infrastructure, credentials, production data, TLS certificates, and Apple signing or release configuration remain deployment concerns and are not committed here.
