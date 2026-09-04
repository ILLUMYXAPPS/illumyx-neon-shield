# Neon Shield Real-Device Smoke Test Plan

## Purpose

This checklist defines the real-device verification required before treating mobile runtime behaviour as release-ready. It complements automated CI and does not replace production authentication, signing, or independent security review.

## Official first-device target

**Primary device: iPad 16**

The iPad 16 is now the official first real-device target for Neon Shield smoke testing because its UDID has been obtained and the device can be prepared for Apple registration/provisioning. The raw UDID is intentionally not stored in this repository or in test evidence.

The remaining authorised test devices are:

- Apple iPhone 15 Pro
- Apple iPhone 16 Pro

They remain part of the authorised test-device set and will follow the iPad 16 once the first-device gate is completed.

Record the actual OS version, app build/version, test date, and test environment for each run.

## First-device gate

The iPad 16 should be used first for the critical end-to-end path:

1. Apple device registration/provisioning
2. Signed iOS build installation through the approved distribution path
3. Fresh install and five-step onboarding
4. Owner initialisation and persisted bootstrap verification
5. Trusted/untrusted-device enforcement
6. Blocked identity and blocked phone enforcement
7. Session expiry, revocation, and refresh rotation
8. Network failure and fail-closed behaviour
9. HTTPS and sensitive-data leakage checks
10. Security-event verification
11. Preservation of test evidence and any defects

The iPhone 15 Pro and iPhone 16 Pro then provide cross-device confirmation of equivalent authoritative policy outcomes.

## Evidence rule

For every test, record:

- Test ID
- Device and OS
- Build/version
- Preconditions
- Action performed
- Expected result
- Observed result
- Pass/Fail
- Evidence reference
- Notes or defect ID if applicable

Do not record passwords, session tokens, private keys, raw device identifiers, or other secrets in screenshots, logs, or test notes.

## Smoke tests

| ID | Test | Expected result | Status |
|---|---|---|---|
| RD-01 | Fresh install | App launches without exposing protected dashboard before required bootstrap state is available | ⬜ Not run |
| RD-02 | First-run onboarding | Five-step onboarding appears for an uninitialised owner | ⬜ Not run |
| RD-03 | Owner initialisation | Owner setup completes through the intended security service boundary | ⬜ Not run |
| RD-04 | Onboarding completion | Completion state is persisted only after owner initialisation is confirmed | ⬜ Not run |
| RD-05 | Restart | App reloads persisted state safely and does not bypass security checks | ⬜ Not run |
| RD-06 | Trusted device | Authorised device can reach protected operations after valid server-side/device policy verification | ⬜ Not run |
| RD-07 | Untrusted device | Untrusted device cannot obtain protected access | ⬜ Not run |
| RD-08 | Device removal | Removing a trusted device causes subsequent protected access/session use to be rejected by the authoritative policy boundary | ⬜ Not run |
| RD-09 | Blocked identity | Blocked identity is rejected before protected session issuance | ⬜ Not run |
| RD-10 | Blocked phone | Blocked phone identity is rejected before protected session issuance | ⬜ Not run |
| RD-11 | Session expiry | Expired session cannot be reused for protected operations | ⬜ Not run |
| RD-12 | Session revocation | Revoked session cannot be reused | ⬜ Not run |
| RD-13 | Refresh rotation | Refresh produces the expected rotated session identifier and invalidates the prior session as designed | ⬜ Not run |
| RD-14 | Network failure | Protected operations fail closed when required server security state cannot be verified | ⬜ Not run |
| RD-15 | HTTPS | Production-like non-local communication uses HTTPS only | ⬜ Not run |
| RD-16 | Security events | Security events are recorded without credentials, tokens, raw phone numbers, or raw device identifiers | ⬜ Not run |
| RD-17 | No sensitive leakage | UI, logs and diagnostics do not expose secrets or security-sensitive identifiers | ⬜ Not run |
| RD-18 | Multi-device consistency | The authorised devices observe the same authoritative policy outcome for equivalent tests | ⬜ Not run |

## Execution order

1. Capture iPad 16 build/environment metadata without recording its raw UDID.
2. Complete Apple device registration and matching provisioning profile setup.
3. Install the signed build through the approved distribution path.
4. Run fresh-install and onboarding tests on the iPad 16.
5. Verify owner initialisation and persisted bootstrap state.
6. Run trusted/untrusted-device tests.
7. Run block and session enforcement tests against a production-like backend.
8. Exercise network failure and fail-closed behaviour.
9. Review logs/audit events for sensitive-data leakage.
10. Repeat critical policy tests on the iPhone 15 Pro and iPhone 16 Pro.
11. Preserve evidence and record defects without deleting failed history.

## Release rule

A smoke-test pass does not by itself establish production readiness. The final release gate requires the applicable automated checks, production infrastructure controls, signing validation, monitoring/alerting, and independent security review to be completed as defined by `FINAL_RELEASE_GATE.md`.

The project percentage must not increase merely because a test was attempted. A meaningful increase requires a completed and verified gate.

## ILLUMYX Way

> Today we build.
>
> Together we grow.
>
> We don't hide the challenges. We learn from them.
>
> We don't erase the history. We build on it.
>
> We don't rush what matters. We earn every step.
>
> One green light at a time.
