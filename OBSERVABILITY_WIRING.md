# Observability Wiring

Neon Shield now wires the application authentication service to an injected `SecurityEventSink`.

## Runtime rules

- Development/integration defaults to `NoopSecurityEventSink` unless a sink is explicitly supplied.
- Production requires both a managed `ManagedAuthStore` and an injected `SecurityEventSink`.
- Production composition therefore cannot silently fall back to a no-op monitoring sink.
- Security events contain UTC timestamps, request-independent safe metadata, and hashed subject/device identifiers only.
- Raw credentials, session tokens, passwords, session secrets, identities, and raw device identifiers are not emitted as event fields.

## Instrumented events

The authentication service emits events for:

- authentication failures
- rate limiting
- blocked identities and phones
- untrusted devices
- successful session issuance
- invalid, rejected, expired, blocked, or untrusted sessions
- session refresh
- session revocation

The provider implementation remains a deployment concern. Monitoring credentials, endpoints, retention, alerting and on-call routing must be supplied outside application source code.
