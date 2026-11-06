# Universal device pairing: independent review checklist

## Review scope

- Pull request: #156, `feature/universal-device-pairing`
- Customer flow: six-digit code and request reference only
- QR rendering, camera scanning and camera permissions are intentionally excluded
- This checklist is a handoff aid, not evidence that an independent review has occurred

## Implementation files

- `backend/device_pairing.py`
- `backend/device_pairing_test.py`
- `backend/http_api.py`
- `backend/managed_db_store.py`
- `backend/production_migrations.py`
- `backend/migrations_test.py`
- `mobile/lib/auth/device_pairing_api.dart`
- `mobile/lib/auth/https_auth_api.dart`
- `mobile/lib/auth/device_pairing_screen.dart`
- `mobile/lib/auth/connected_devices_screen.dart`
- `mobile/test/device_pairing_api_test.dart`
- `mobile/test/device_pairing_screen_test.dart`
- `docs/DEVICE_PAIRING_SPEC.md`

## Security review acceptance criteria

- [ ] Confirm the six-digit code is generated using a cryptographically secure random source.
- [ ] Confirm the code and polling secret are stored only as keyed hashes using the deployment pepper.
- [ ] Confirm the polling secret can check status but can never approve a device.
- [ ] Confirm approval requires a live, server-verified trusted session for the same account.
- [ ] Confirm requests expire after five minutes and no more than five incorrect codes are accepted per request.
- [ ] Confirm successful approval is atomic, single-use and resistant to concurrent replay.
- [ ] Confirm cross-account approvals, expired requests, revoked approvers and replay attempts fail closed.
- [ ] Confirm unlinking revokes the device's trust and active sessions atomically.
- [ ] Confirm device inventory and references do not expose raw device identifiers or another account's devices.
- [ ] Confirm HTTP errors do not reveal account existence, credentials, codes or polling secrets.
- [ ] Confirm production requests require HTTPS and sensitive values never appear in URLs or logs.
- [ ] Confirm SQLite and managed DB transaction/locking behaviour is correct for the supported database engines.
- [ ] Confirm migration 4 upgrades an existing version-3 database and is safe to apply through the migration runner.
- [ ] Confirm Flutter screens handle expired requests, network failures, invalid codes and revoked sessions safely.

## Tests to inspect or add during review

- [ ] Wrong-code attempt limit and lockout.
- [ ] Expiry before and during approval.
- [ ] Cross-account approval and device inventory isolation.
- [ ] Replay and concurrent approval attempts.
- [ ] Polling with an incorrect secret and after expiry.
- [ ] Revoked approver session.
- [ ] Unlinking prevents further use and refresh of the removed device's sessions.
- [ ] HTTP start/approve/status contract uses the six-digit code only.
- [ ] Migration from an existing version-3 production schema to version 4.
- [ ] Flutter widget behaviour for the six-digit-only customer journey.

## Known release blockers

These are not represented as completed by green CI:

- IP/edge rate limiting at the trusted production proxy/WAF.
- Step-up authentication for sensitive device-management actions.
- Server-side Premium/Family entitlement enforcement after exact product limits are approved.
- Apply and verify production migration version 4 against the actual managed database.
- Production HTTPS/reverse-proxy configuration, secret management, monitoring, backup and restore validation.
- Physical-device testing on iOS/iPadOS and Android devices.
- Independent external security review and resolution of all findings.

## Release boundary

Keep PR #156 in draft. Do not merge, bypass branch protection, or describe universal pairing as production-ready until the independent reviewer has completed the review, all findings are resolved, production controls are verified, and physical-device testing is recorded.
