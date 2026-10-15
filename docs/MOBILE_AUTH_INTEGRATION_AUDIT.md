# Mobile Authentication Integration Audit

**Audit refresh:** 2026-10-10  
**Scope:** Repository-side review of the Flutter app entry point, onboarding, auth gate, service, HTTPS adapter, secure session storage, tests, and release gates.  
**Environment:** Source and GitHub Actions review only. No live backend credentials, deployed non-production endpoint, or physical device was available for end-to-end testing.

## Summary

The previous integration-gap finding is now partially resolved in the current `main` source: `mobile/lib/main.dart` constructs `ServerBackedAuthService` when `NEON_SHIELD_AUTH_BASE_URL` is supplied, using `HttpsAuthApi` and `SecureAuthSessionStore`, and places `AuthGate` between onboarding and the dashboard. Missing endpoint configuration fails closed unless the explicit local-beta flag is enabled.

This is meaningful application wiring, but it is **not evidence of a working deployed authentication system**. The configured backend, account/owner enrollment and recovery flow, trusted-device policy, production secrets/persistence, and live end-to-end behavior remain unverified.

## Verified in source

- `AppBootstrap` reads `NEON_SHIELD_AUTH_BASE_URL` at build time and constructs the server-backed auth service.
- The default production path does not show the dashboard if no auth service is configured; local-beta dashboard access requires explicit `NEON_SHIELD_ALLOW_LOCAL_BETA`.
- `AuthGate` restores a stored session through the service, supports sign-in/sign-out, and locks the dashboard when a session expires or cannot be verified.
- `HttpsAuthApi` and the auth service have separate unit tests, and platform secure storage is abstracted behind `SecureAuthSessionStore`.
- The dashboard labels local setup/device records as local state and explicitly discloses that active malware scanning, threat blocking, and broader file protection are not implemented.
- The current `main` version of `ServerBackedAuthService` does not yet compare the session's returned device ID with the initiating device ID during sign-in or ensure that refresh preserves the current device binding. PR #94 proposes that defense-in-depth and has passing reported CI checks, but remains unmerged and has no submitted reviews.

## Remaining gaps

- No live non-production backend or end-to-end run has verified TLS, real credentials, server-side trusted-device enforcement, blocked identities, refresh rotation, revocation, expiry, or server outage behavior.
- The production HTTPS endpoint, managed database, secret provider, durable security-event delivery, and monitoring/alert routing are not deployed and verified.
- Owner enrollment, recovery/re-enrollment, and any required phone-identity policy need an explicit server-backed design. The client must not infer server trust from a local device identifier or onboarding flag.
- Real iOS and Android device checks, secure-storage behavior, platform signing, store readiness, and independent review of the completed integration remain open.

## Required next steps

1. Review PR #94's device-binding change and obtain the repository-required approvals before considering merge. Do not bypass branch protection.
2. Configure a disposable non-production HTTPS backend and test account without embedding secrets in source or build arguments.
3. Execute end-to-end cases for successful and failed sign-in, trusted/untrusted devices, blocked identity policy, refresh rotation, expiry, revocation, and backend outage.
4. Verify owner enrollment and recovery/re-enrollment behavior once implemented.
5. Run fresh mobile analysis, all Flutter tests, Python/security regressions, and mobile builds against the candidate source.
6. Test critical flows on supported physical iOS and Android devices and record device/OS/build evidence.
7. Obtain independent security review and preserve findings, remediation, and retest evidence.

## Release decision

**Status: Open.** Source-level authentication wiring is present, but live authentication, production infrastructure, device verification, signing, and operational evidence are not. Green pull-request checks are useful evidence of code health, not proof of production readiness.
