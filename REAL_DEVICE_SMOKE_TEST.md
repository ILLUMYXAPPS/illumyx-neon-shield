# Neon Shield Real-Device Smoke Test Plan

## Purpose

This checklist defines the real-device verification required before treating mobile runtime behaviour as release-ready. It complements automated CI and does not replace production authentication, signing, or independent security review.

## Test devices

Use the three authorised test devices when physically available:

- Apple iPhone 15 Pro
- Apple iPhone 16 Pro
- iPad 16

Record the actual OS version, app build/version, test date, and test environment for each run.

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
| RD-18 | Multi-device consistency | The three authorised devices observe the same authoritative policy outcome for equivalent tests | ⬜ Not run |

## Execution order

1. Capture device/build/environment metadata.
2. Run fresh-install and onboarding tests.
3. Verify owner initialisation and persisted bootstrap state.
4. Run trusted/untrusted-device tests.
5. Run block and session enforcement tests against a production-like backend.
6. Exercise network failure and fail-closed behaviour.
7. Review logs/audit events for sensitive-data leakage.
8. Repeat critical policy tests across the authorised device set.
9. Preserve evidence and record defects without deleting failed history.

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
