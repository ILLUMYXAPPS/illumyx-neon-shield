# Neon Shield Cross-Platform Ecosystem Audit

Audit target: `feature/controlled-validation-ecosystem-audit`, based on PR #159 head `a8764557a9ee095ab64e644190256f4f50553200`.

Audit type: repository source, workflow and automated-test inventory. This is not an independent security audit, production deployment review, or physical-device certification.

## Audit rules

- **Implemented / test-covered** means source and automated tests are present. It does not mean the feature has been independently validated in production.
- **Partial** means some platform, integration, service, or enforcement work remains.
- **Not verified** means repository evidence does not yet demonstrate the claimed end-to-end behaviour.
- A cloud simulator or hosted desktop runner is not a physical customer device.
- The same feature should have consistent customer-facing intent and terminology across platforms, while respecting native platform conventions.
- Do not claim parity merely because a shared Flutter codebase builds on multiple operating systems.

## Platform coverage snapshot

| Platform | Repository evidence | Current evidence | Remaining proof |
|---|---|---|---|
| Android | Flutter mobile app, Android build workflow, emulator launch smoke | CI build and hosted emulator launch checks have passed on recorded runs | Signed install/update on physical Android hardware; vendor-specific behaviour, including Google and Samsung devices |
| iPhone | Shared Flutter app, iOS simulator workflow, unsigned iOS build | Hosted iPhone simulator build/install/launch coverage exists | Signed install, real-device permissions, lifecycle, secure storage and upgrade checks |
| iPad | Shared Flutter app and iPad simulator workflow | Hosted iPad simulator smoke coverage exists | Physical iPad layout, rotation, multitasking, accessibility and signed upgrade checks |
| Windows | Flutter Windows target and desktop smoke workflow; separate Python desktop app source | Hosted Windows build/launch smoke coverage exists | Supported physical Windows versions, permissions, firewall/Defender integration and update behaviour |
| macOS | Flutter macOS target and desktop smoke workflow | Hosted macOS build/launch smoke coverage exists | Signed physical Mac testing, Keychain/permissions, firewall/security integration and update behaviour |

## Feature and cross-platform consistency register

| Feature area | Evidence in source/tests | Cross-platform assessment | Next verification |
|---|---|---|---|
| App bootstrap and onboarding | `mobile/lib/main.dart`, onboarding screen and bootstrap tests | Shared Flutter flow; device-specific first-run behaviour not yet established | Fresh install, restart and persisted owner setup on each supported device family |
| Authentication and sessions | Auth gate/service/session code and Dart/Python regression tests | Shared client contract with backend security boundary | Verify deployed non-production identity service, expiry, revocation, refresh and concurrency |
| Six-digit device pairing | Pairing API/screen/service and backend pairing tests | Shared six-digit flow is represented in client and backend | Run live two-device pairing, invalid/expired/replayed code, approval/rejection and unlink revocation |
| Connected-device management | Connected devices screen and pairing API tests | UI/API coverage exists | Verify unlink blocks subsequent protected backend operations on all supported client types |
| Protection Clipboard | Clipboard screen/service and widget/service tests | Shared mobile feature is present; customer ON/OFF choice must remain visible and effective | Verify toggle state persists, controls the intended protection functions and is consistent across devices |
| Protection profiles | Profile model/service and Python tests | Configuration and contract coverage exists | Verify actual matching/enforcement pipeline; do not describe profile configuration alone as active scanning |
| Security posture | Security service, access blocklist and platform check tests | Platform-specific capability differences are expected | Verify permission handling, unsupported states and real device results; distinguish unavailable from safe |
| Encrypted vault | Encrypted vault service/screen and tests | Shared app implementation with OS-specific secure-storage dependencies | Physical-device key-store failure, interrupted write, reinstall, backup/restore and migration testing |
| Settings and version migrations | `settings_migration_service.dart` and migration tests | Shared versioned migration logic | Verify settings survive successive app upgrades and rollback/failure handling on signed physical devices |
| Network telemetry | Python network telemetry and Windows WFP collector tests | Windows WFP evidence exists; other platforms currently report no events in the audited implementation | Implement native collectors only where supported and permissioned; clearly distinguish no events from unavailable |
| Device sessions | Python session metadata model and tests | Backend metadata coverage exists; not equivalent to OS-level screen-mirroring detection | Verify authoritative backend integration and clearly limit customer-facing claims |
| Neon Forensics | Forensics/vault modules, hash/manifest/export tests | Evidence model and automated coverage exist | Verify durable storage, access controls, retention, export integrity and incident workflow in deployed test environment |
| Entitlements/subscriptions | Entitlement policy model and tests | Policy logic exists; live billing provider integration not evidenced | Verify provider webhooks, renewal, expiry, refunds, family membership and restore purchases |
| Desktop security checks | Python security checks, device panel and tests | Read-only host checks and graceful unavailable states are covered | Validate on supported physical Windows/macOS hosts with least privilege |
| Copyright/file matching | Scanner, matching and review-pipeline modules/tests | Automated matching and review modules exist | Validate dataset provenance, false positives/negatives and user review workflow |
| Privacy/data handling | Sensitive-field filtering and security tests | Some controls are covered in automated tests | Inspect end-to-end logs, telemetry, crash reports and network traffic on release candidates |
| Navigation and terminology | Shared Flutter feature screens and cross-platform build workflows | Shared code can support consistent navigation; visual/interaction parity is not yet demonstrated by build success | Capture comparable screen-by-screen journeys on phone, tablet, Windows and Mac; record differences and accessibility checks |

## Immediate parity test journeys

Run these journeys on each platform where the feature is supported. Record unsupported capabilities explicitly rather than treating them as failures or silently omitting them.

1. First launch, onboarding and owner setup.
2. Sign-in, session expiry, sign-out and restart.
3. Six-digit pairing, approval/rejection, expiry and device unlink.
4. Protection Clipboard: view settings, switch each customer-facing toggle ON/OFF, restart and confirm persistence.
5. Protection profiles: select/configure a profile and verify the actual enforcement result.
6. Vault: create, read, modify and safely handle a failed or interrupted operation.
7. Settings upgrade: install an older test build, configure settings, upgrade to the candidate and verify preservation.
8. Accessibility: text scaling, keyboard/focus navigation where applicable, screen reader labels, contrast and reduced motion.
9. Network interruption: confirm protected operations fail closed where required and the UI explains the state.
10. Recovery from app restart, update and supported reinstall paths.

## Evidence record template

For each journey record:
- Test ID and feature
- Platform, device model and OS version
- App version/build and commit SHA
- Preconditions and test data class (test account only)
- Action and expected outcome
- Observed outcome and PASS / FAIL / PARTIAL / NOT RUN
- Evidence reference and defect/PR link
- Notes on native platform differences

Never store passwords, session tokens, private keys, raw device identifiers or other secrets in test evidence.

## Known external gates

The repository's existing release and production-like test plans identify additional work that cannot be satisfied by CI alone:

- Managed production-like backend, TLS, durable storage, secrets, backups and restore evidence.
- Real identity/recovery integration and independent review.
- Live billing provider integration before subscriptions can be called operational.
- Signed physical-device testing and store-upload validation.
- Independent application/security review, remediation and retest.
- Monitoring, alert delivery and durable audit retention.

## Recommended execution order

1. Keep existing successful CI evidence intact.
2. Run one manually selected validation batch at a time using `.github/workflows/controlled-validation.yml`.
3. Complete a screen-by-screen parity audit, recording actual differences rather than assuming parity.
4. Fix only demonstrated defects and add regression coverage.
5. Repeat physical-device and production-like tests when signing and infrastructure are available.
6. Submit for independent review; preserve all findings and remediation evidence.
7. Reassess release readiness only after the relevant gates have evidence.

## Audit conclusion

Neon Shield has a shared cross-platform application foundation and automated build/test coverage for Android, iPhone, iPad, Windows and macOS. The current repository evidence supports **cross-platform build and selected hosted smoke-test coverage**, not complete feature parity or production readiness. The next meaningful step is evidence-led journey testing on each platform, with differences and unavailable capabilities documented honestly.
