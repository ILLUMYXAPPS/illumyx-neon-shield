# Production Observability Contract

Neon Shield uses a provider-neutral `SecurityEventSink` boundary for security monitoring.

## Production requirements

- Inject a managed monitoring/security-event implementation at deployment time.
- Events must use UTC timestamps and correlation/request IDs where available.
- Subject and device identifiers must be hashed before emission. Raw credentials, tokens, passwords, session secrets, and raw device identifiers must never be emitted.
- Monitoring configuration and credentials must come from deployment-managed secret/configuration systems.
- Production monitoring endpoints must use HTTPS.
- Delivery failures must be visible to the deployment platform and must not silently become successful security events.
- The monitoring provider must support retention, access control, alerting, and auditability appropriate to production security events.

## Development

Development may use `NoopSecurityEventSink`. This sink does not satisfy the production monitoring requirement.

## Event categories

Implementations should support, at minimum:

- authentication failures and successes
- blocked identity/device/phone events
- session creation, refresh, and revocation
- suspicious or rate-limited activity
- security-policy violations

This contract defines the application boundary only. Provisioning the managed monitoring service, alert rules, credentials, retention policy, and on-call routing remains a production deployment responsibility.
