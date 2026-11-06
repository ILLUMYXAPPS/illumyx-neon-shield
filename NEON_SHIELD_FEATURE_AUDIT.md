# Neon Shield Feature Health Audit

Audit target: integration/neon-shield-ios-smoke-2026-11-06
Baseline commit reviewed: 623365d1af29a97ca80d8da5c438c647330457fa
Audit type: source and test inventory review. This is not an independent security audit or real-device test.

## Evidence already present

- Combined CI run reported successful mobile builds for Windows, Android, macOS and unsigned iOS.
- iPhone and iPad cloud simulator smoke jobs reported success.
- Python tests, Flutter tests, mobile checks, CodeQL, secret scan, security gate and Pylint reported success.
- Feature-specific test files exist for authentication, auth sessions, pairing, vault, onboarding, protection profiles, security service, device sessions, entitlements, forensics, platform collectors, network telemetry, and desktop security checks.

## Feature register

| Feature area | Source/test evidence | Assessment | Remaining verification |
|---|---|---|---|
| App bootstrap and onboarding | mobile/lib/main.dart; app_bootstrap_test.dart; onboarding_screen_test.dart | Automated coverage exists | Fresh install/restart on signed devices; verify owner setup and persisted state |
| Authentication and sessions | auth_service.dart; auth_gate.dart; auth_server tests; auth_gate_test.dart; auth_service_test.dart | Application logic and regression coverage exist | Test against deployed non-production identity service; invalid credentials, rate limits, expiry, revocation and refresh concurrency |
| Six-digit device pairing | device_pairing_screen.dart; device_pairing_api_test.dart; device_pairing_screen_test.dart | Six-digit manual pairing flow implemented and widget-tested | Live service approval, rejection, expiry, replay and concurrent polling tests |
| Connected-device management | connected_devices_screen.dart and pairing API tests | API/UI coverage exists | Verify unlink/revocation prevents subsequent protected access on backend |
| Encrypted local vault | encrypted_file_vault.dart; encrypted_file_vault_test.dart; encrypted_vault_screen_test.dart | Encryption, authenticated decryption, malformed/tampered envelope and recovery paths have tests | Test key-store failure, interrupted writes, app reinstall, backup/restore and device migration on physical devices |
| Vault key recovery | vault key-store implementation and recovery tests | Local authenticated orphan-file recovery exists; no independent cloud key recovery integration evidenced | Define and independently review any account-level recovery design; never promise recovery if device key is lost |
| Protection profiles | protection_profile.dart; protection_profile_service_test.dart; protection_profiles.py tests | Profile configuration and contract tests exist | Verify actual matching/enforcement pipeline; mobile profile model alone is configuration, not scanning/enforcement |
| Security posture checks | security_service.dart; security_service_test.dart; security_checks.py tests | Local state and platform check coverage exists | Verify OS-specific permissions, unsupported states and real-device outputs |
| Network telemetry | network_telemetry.py; windows_wfp_telemetry.py; tests | Windows reads existing WFP audit events; other platforms currently return no events | Implement/test native collectors only where supported and permissioned; UI must clearly show unavailable vs no events |
| Device sessions | device_sessions.py; test_device_sessions.py | Session metadata model tested | Verify integration with authoritative backend; metadata is not OS-level screen mirroring detection |
| Neon Forensics | neon_forensics.py; neon_forensics_vault.py; related tests | Evidence model, hashes, manifest and export have tests | Verify durable production storage, access controls, retention, export integrity and incident workflow |
| Subscription entitlements | entitlements.py; test_entitlements.py | Server-authoritative policy model tested | Connect verified billing provider/webhooks and test renewals, expiry, refunds, family membership and restore purchases |
| Desktop firewall/Defender | security_checks.py; device_security_panel.py; tests | Read-only platform checks and graceful unavailable states are tested | Test on supported physical Windows/macOS hosts and verify least privilege |
| Copyright/file matching | match_scanner.py; copyright_match_engine.py; review pipeline tests | Matching and review modules have automated tests | Validate source datasets, false-positive/negative handling and user review workflow |
| Production backend | backend service/store; tests/test_production_backend.py; production docs | Local/persistent adapter tests exist | Deploy disposable non-production environment with managed DB, TLS, secrets, migrations, backups, alerts and audit retention |
| Privacy and data handling | forensics field policies, security and backend tests | Some sensitive-field filtering is tested | End-to-end log, telemetry, crash-report and network inspection on release candidates |

## Blocking external or deployment gates

1. Production-like backend and managed infrastructure are not evidenced as deployed.
2. Recovery/identity verification integration is not implemented according to the production-like test plan.
3. Actual billing provider integration is required before live subscriptions can be treated as operational.
4. Physical-device smoke testing remains pending; cloud simulator tests do not replace it.
5. iOS and Android release signing and store-upload validation remain pending.
6. Independent external security review and remediation/retest remain required.
7. Monitoring/alert delivery, durable audit storage and verified backup restoration require deployment evidence.

## Execution order

1. Keep current successful CI evidence intact.
2. Run all focused Flutter and Python tests on the current audit head after any code changes.
3. Address reproducible defects with regression tests; do not change passing code without a demonstrated defect.
4. Complete backend integration tests in a disposable non-production environment.
5. Complete real-device tests after signing and provisioning are available.
6. Obtain independent review, remediate findings, and retest.
7. Only then reassess release readiness.

## Status vocabulary

- PASS: behaviour was exercised by an automated test or recorded run.
- PARTIAL: code/tests exist, but an integration, platform, or real-device gate remains.
- NOT IMPLEMENTED/NOT DEPLOYED: required capability or deployment evidence is absent.
- NOT VERIFIED: source or tests do not establish the claimed end-to-end behaviour.

A passing CI run is evidence of tested code paths, not proof that every feature is production-ready, secure, or stable under real-world conditions.
