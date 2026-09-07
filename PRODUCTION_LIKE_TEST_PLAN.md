# Neon Shield Production-Like Security Test Plan

## Scope

Disposable non-production environment only. Use test identities, test devices and test secrets. Never use production credentials or real sensitive data.

## Environment checks

- [ ] PostgreSQL is managed and reachable only over TLS.
- [ ] Production configuration validation succeeds with injected secrets.
- [ ] Missing required dependencies fail closed.
- [ ] Versioned migrations complete before application startup.
- [ ] Connection pooling and bounded timeouts are configured.
- [ ] Monitoring event delivery is verified.
- [ ] Warning and critical security alerts are delivered.
- [ ] Backup evidence and restore verification are recorded.

## Authentication checks

- [ ] Valid credentials authenticate successfully.
- [ ] Invalid credentials fail without revealing account existence.
- [ ] Repeated failures trigger rate limiting.
- [ ] Trusted device can authenticate.
- [ ] Untrusted device is rejected where required.
- [ ] Blocked identity is rejected.
- [ ] Blocked phone is rejected.
- [ ] Session expires at the configured boundary.
- [ ] Revoked session cannot be used.
- [ ] Refresh rotation consumes the old session atomically.
- [ ] Two concurrent refresh attempts cannot both consume the same old session.
- [ ] Audit events contain no raw credentials or session tokens.
- [ ] Warning/critical events reach the configured alert sink.

## Recovery/identity checks

These remain blocked until an actual recovery/identity-verification integration exists.

- [ ] Recovery token is single-use.
- [ ] Recovery token expires.
- [ ] Replayed recovery token is rejected.
- [ ] Recovery is rate limited.
- [ ] Recovery does not disclose account existence.
- [ ] Identity verification failure is fail-closed.
- [ ] Recovery and verification events are audited safely.
- [ ] Independent review and retest completed.

## Mobile checks

For every supported candidate device:

- [ ] Install candidate build.
- [ ] Complete authentication.
- [ ] Confirm trusted-device state.
- [ ] Verify protected operation.
- [ ] Revoke device.
- [ ] Verify protected operation is rejected after revocation.
- [ ] Re-enroll device through intended flow.
- [ ] Repeat after update/reinstall where applicable.

Record: device model, OS version, app version, build identifier, test date, result and evidence reference.

## Exit criteria

The environment is not considered production-like validated until all applicable checks have evidence. Failed checks require remediation and regression coverage before retest.
