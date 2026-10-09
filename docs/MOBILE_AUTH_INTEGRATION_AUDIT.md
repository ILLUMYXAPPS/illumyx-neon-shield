# Mobile Authentication Integration Audit

**Audit date:** 2026-10-09  
**Scope:** Repository-side review of the Flutter app entry point, onboarding, mobile auth abstractions, HTTPS adapter, secure session storage, and existing unit tests.  
**Environment:** Source review only. No production environment or non-production backend credentials were supplied, so no live backend integration test was attempted.

## Summary

The repository contains a meaningful authentication foundation and unit tests, but the main Flutter app does not yet construct or use the server-backed authentication service. The app currently loads local owner/trusted-device state through `SecurityService` and enters the dashboard based on local onboarding and owner-initialization state. That local posture must not be represented as a server-authenticated session.

## What exists

- `mobile/lib/auth/auth_api_contract.dart`: provider-neutral sign-in, refresh, revoke, and trusted-device contract.
- `mobile/lib/auth/https_auth_api.dart`: HTTPS API adapter. Non-loopback plaintext HTTP is rejected.
- `mobile/lib/auth/auth_service.dart`: server-backed session lifecycle orchestration, including trusted-device checks before persisting or restoring a session.
- `mobile/lib/auth/secure_auth_session_store.dart`: platform secure-storage adapter for the session material.
- `mobile/test/auth_service_test.dart`: unit tests for sign-in, untrusted devices, refresh, expiry, revoke failure, and session restoration.
- `mobile/test/https_auth_api_test.dart`: unit tests for HTTPS enforcement, request shape, bearer auth, and typed credential failures.
- `mobile/test/secure_auth_session_store_test.dart`: secure-session persistence tests, including malformed stored data.

## Integration gap confirmed

- `mobile/lib/main.dart` does not import or construct `ServerBackedAuthService`, `HttpsAuthApi`, or `SecureAuthSessionStore`.
- `AppBootstrap` and the dashboard currently use local `SharedPreferences` onboarding state and `SecurityService`.
- `mobile/lib/onboarding/onboarding_screen.dart` describes account and device-verification steps but does not collect credentials or perform server sign-in.
- The mobile API base URL, production endpoint configuration, and owner credential/recovery flow are not defined in the reviewed app entry point.
- The mobile `AuthApiContract.signIn` and `HttpsAuthApi.signIn` currently send identity, credential, and device ID only. If phone identity is required by the server's authorization policy, its collection, privacy treatment, and transport must be explicitly designed before integration; do not silently infer it from other fields.
- Existing tests are unit/contract tests with fake APIs or mock HTTP responses. They do not prove integration with a running backend, real TLS configuration, production persistence, or real-device platform storage.

## Safety decision

Do not wire the auth service directly into the dashboard yet. First define the intended owner/account setup flow, non-production endpoint configuration, device identifier lifecycle, recovery/re-enrollment behavior, and UI states for unavailable, expired, revoked, and untrusted sessions. Local owner flags or device IDs must never be treated as server-issued authentication proof.

## Required next implementation and verification sequence

1. Agree the owner identity and credential setup/recovery flow without putting credentials into onboarding preferences or logs.
2. Add an explicit environment configuration boundary for the non-production HTTPS API endpoint. Production must reject missing or non-HTTPS endpoints; do not add a silent production fallback.
3. Define how a stable device identifier is generated, stored, rotated, and revoked without relying on a client-provided trusted flag.
4. Integrate `ServerBackedAuthService` into bootstrap through dependency injection, with explicit unauthenticated, loading, authenticated, expired, revoked, untrusted-device, and unavailable states. A backend outage must not create an authenticated state.
5. Add integration tests against a disposable non-production backend for successful sign-in, invalid credentials, untrusted device, refresh rotation, expiry, revocation, blocked identity/phone policy, and server unavailability.
6. Add tests for owner setup and recovery/re-enrollment, once that flow is implemented.
7. Run Flutter formatting, analysis, all mobile unit tests, security regression tests, and mobile builds after implementation.
8. Test secure storage and critical flows on real supported iOS and Android devices. Record device/OS/build and evidence; an unsigned iOS build is not a signed release.
9. Obtain independent review of the completed flow and production configuration before any production-readiness gate is marked complete.

## Release gate

**Status: Open.** The existing unit tests are valuable and should remain. End-to-end mobile authentication and device-verification are not complete until the integration above is implemented and evidenced.