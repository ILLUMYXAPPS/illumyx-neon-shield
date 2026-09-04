# Neon Shield Final Release Gate

This checklist defines what must be demonstrated before Neon Shield is treated as release-ready. A green CI result is evidence, not a substitute for deployment or independent review evidence.

## Operating principle

> Today we build. Together we grow. One green light at a time.

A gate is marked complete only when the required evidence exists. Failed checks and their remediation history remain part of the project record.

## Gate status

| Gate | Required evidence | Status |
| --- | --- | --- |
| CI and automated security | Fresh CI run for the current source, including security, tests, mobile checks and builds | 🟡 Pending verification for latest transport-gate fix |
| Production HTTPS | Managed TLS, HTTPS-only transport, certificate validity/renewal evidence | ⬜ Not deployed |
| Managed persistence | Durable production storage for identities, trusted devices, blocks, sessions and audit events | ⬜ Not deployed |
| Production secrets | Deployment-platform secret manager configured and verified | ⬜ Not deployed |
| Production authentication | Server-authoritative authentication exercised against a non-production test account | ⬜ Not deployed |
| Trusted-device enforcement | Removal/revocation blocks subsequent session use or refresh | ⬜ Not verified in production-like environment |
| Block enforcement | Blocked identity and blocked phone checks verified end-to-end | ⬜ Not verified in production-like environment |
| Session security | Expiry, revocation and refresh rotation verified end-to-end | ⬜ Not verified in production-like environment |
| Security audit trail | Durable events, safe correlation data and audit-chain integrity verification | ⬜ Not deployed |
| Monitoring and alerting | Authentication, abuse, service, database and audit-integrity alerts verified | ⬜ Not deployed |
| Real-device smoke test | iPhone 15 Pro, iPhone 16 Pro and iPad 16 test plan executed on available release builds | ⬜ Pending device execution |
| Release signing | Android/iOS signing validation and store-upload readiness | 🟡 Pipeline hardened, final signing evidence pending |
| Independent security review | Independent scope, findings, remediation and retest evidence | ⬜ Not completed |
| Store/release readiness | Store metadata, privacy/support material and production configuration verified | ⬜ Pending final release preparation |

## Evidence rules

1. Do not delete failed runs, failed tests, warnings or remediation history to improve appearances.
2. When a check fails, record the failure, identify the root cause, fix it, add or strengthen regression coverage where appropriate, and rerun the relevant gate.
3. Do not increase the internal readiness percentage merely because work was attempted. Increase it only when a meaningful release gate has been verified.
4. Do not describe the project as secure, certified or production-ready solely because CI is green.
5. Independent review findings are not failures of the process by themselves. The required response is reproduce, remediate, verify and preserve the evidence.

## Real-device smoke-test sequence

For each supported test device:

1. Install the candidate build.
2. Confirm first-run onboarding appears only when required.
3. Complete owner setup through the intended flow.
4. Confirm trusted-device state is established through the intended security boundary.
5. Verify protected operations behave correctly for a trusted device.
6. Remove/revoke the device and verify protected access is denied as designed.
7. Exercise the relevant recovery/re-enrollment path.
8. Repeat the critical checks after reinstall/update where applicable.
9. Record build version, device model, OS version, test date, result and any failure/remediation reference.

## Independent review evidence pack

Preserve, rather than rewrite away, the project's development history:

- security and architecture documents
- relevant commits and pull requests
- failed CI runs and their root-cause fixes
- regression tests added after failures
- successful reruns
- signing-pipeline hardening evidence
- production-boundary decisions
- known limitations and remaining gates
- final remediation and retest evidence from the independent reviewer

## Final release decision

The final release decision requires all applicable production, signing, device, operational and independent-review gates to have evidence. The project must remain at its current readiness percentage until a completed gate materially reduces the remaining distance to release.
