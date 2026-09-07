# Production Monitoring & Alert Hardening

Neon Shield keeps monitoring provider-neutral while making the security boundary fail closed and making actionable security events routable to an injected alert destination.

## Application boundary

`backend.security_monitoring.ProductionSecurityMonitor` sits between authentication telemetry and the deployment's monitoring provider.

It enforces:

- security event names remain within the `auth.*` and `session.*` namespaces;
- subject and device identifiers must already be lowercase SHA-256 digests;
- request IDs are bounded and cannot be empty;
- event metadata is limited to the non-sensitive keys `reason` and `event`;
- metadata values are bounded to prevent accidental telemetry expansion;
- monitoring delivery failures propagate instead of being silently treated as successful delivery.

The monitor does not log, transform, store, or transmit passwords, credentials, session tokens, client secrets, raw identities, or raw device identifiers.

## Alert routing

The application classifies events into deterministic severities:

- **Critical:** blocked identities/phones, untrusted devices, and rate limiting.
- **Warning:** authentication failures and rejected/invalid/expired sessions.
- **Info:** successful session lifecycle events and other non-actionable telemetry.

Critical and warning events are forwarded to the injected `SecurityAlertSink`. The sink is provider-neutral and owns the actual delivery mechanism, credentials, endpoint, retry policy, retention, and on-call routing.

Development can use the no-op alert sink. Production must inject a real alert implementation alongside the existing production `SecurityEventSink`.

## Failure behavior

If monitoring delivery fails, the exception is propagated to the caller/deployment platform. The application must not report a successful security event when its monitoring delivery failed.

If alert delivery fails after the event has been accepted by the monitoring sink, the alert delivery exception is also propagated. Deployment infrastructure must therefore provide durable/retriable alert delivery without putting secrets into application telemetry.

## Production responsibilities

The deployment environment remains responsible for:

1. supplying the real monitoring and alert sinks;
2. storing monitoring credentials outside source control;
3. using HTTPS for external monitoring endpoints;
4. configuring retention and access controls;
5. creating alert thresholds, escalation and on-call routing;
6. monitoring sink health and delivery latency;
7. testing alert delivery before production release and after material monitoring changes.

This change does not claim that an external monitoring provider or alerting infrastructure has been provisioned.

## Apple boundary

No Apple signing, provisioning, certificates, TestFlight, or iOS release configuration is required or changed by this hardening step.
