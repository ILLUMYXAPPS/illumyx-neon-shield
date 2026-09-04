# Neon Shield Final 3% Acceptance Gates

## Purpose

This document converts the final release stretch into explicit, evidence-based gates. The project percentage is an internal progress indicator representing distance from the final verified release/security gates. It is not a security score or certification rating.

## Current position

**97%**

The latest production transport security-gate fix has completed successfully. The real-device smoke-test plan is prepared but hardware execution and production-boundary verification remain outstanding.

## 98% Gate: Real-world security behaviour

The 98% gate requires evidence from a production-like environment that the authoritative security boundary correctly enforces:

- Trusted device access is accepted only after authoritative verification.
- Untrusted device access is rejected.
- Removing a trusted device prevents subsequent protected access/session use.
- Blocked identities are rejected before protected session issuance.
- Blocked phone identities are rejected before protected session issuance.
- Expired sessions cannot be reused.
- Revoked sessions cannot be reused.
- Refresh rotates session identifiers as designed.
- Required protected operations fail closed when authoritative security state cannot be verified.
- Security events are persisted without credentials, tokens, raw phone numbers, or raw device identifiers.
- Evidence is captured for each acceptance test.

Required evidence: completed `REAL_DEVICE_SMOKE_TEST.md` results plus production-like backend test evidence where applicable.

## 99% Gate: Production infrastructure

The 99% gate requires the production deployment boundary to be implemented and verified:

- HTTPS-only production transport.
- Managed persistent storage with appropriate access controls and backups.
- Production secrets stored through the deployment platform's secret-management mechanism.
- Server-authoritative credential and session handling.
- Server-side trusted-device registration and revocation.
- Block enforcement at the authoritative boundary.
- Rate limiting and abuse protection appropriate to the deployment.
- Monitoring and security alerting.
- Durable security audit storage and audit-chain integrity verification.
- Production-like automated verification demonstrates the deployed controls behave as designed.

A green CI run alone does not satisfy this gate.

## 100% Gate: Final release readiness

The 100% gate requires all applicable release prerequisites to be complete:

- Real-device smoke testing complete with evidence.
- Android release signing and upload validation complete.
- iOS release signing and upload validation complete.
- Store metadata, privacy disclosures and support/recovery information complete.
- Independent security review completed.
- Security-review findings remediated or formally accepted with documented risk treatment.
- Retesting completed for material findings.
- Final release checklist reviewed and signed off.
- Production monitoring and incident-response readiness confirmed.

## Evidence integrity rule

Never delete a failed run, suppress a warning, rewrite history to make the project appear cleaner, or count an attempted gate as a completed gate.

The evidence chain is:

**Attempt → Result → Investigation → Root cause → Fix → Regression protection → Verification → Green light**

## Percentage rule

No percentage increase is awarded for optimism, preparation, or an attempted action. A percentage increase requires a meaningful gate to be completed and verified.

## Human sustainability rule

Waiting for CI or another external process is not a failure of progress. During waiting periods, the team may deliberately switch to creative work, documentation, music, storytelling, humour, or other restorative activity rather than repeatedly checking the same pending result.

This is part of the project culture:

> If CI is thinking, we don't have to.
>
> Let the machine do its work. Let the mind breathe. Then come back ready for the next green light.

## The ILLUMYX Way

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
>
> And occasionally, one cheesecake at a time.
