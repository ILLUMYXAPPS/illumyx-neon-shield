# Neon Shield Proposed Scan Evidence Policy

> **Status: PROPOSED. Not implemented, tested, or approved for production.**

## Decision rule

### Verified clear result
When a supported scan completes successfully and its result is verified as clear, retain only:
- Scan completion timestamp (including timezone or an unambiguous UTC representation).
- Verification status indicating the result was successfully verified as clear.

Do not retain a full transcript or unnecessary scan details for a verified clear result.

### Non-clear, failed, or uncertain result
When a scan reports an issue, cannot verify a clear result, fails, is cancelled, or is unavailable:
- Preserve the relevant scan transcript or event details needed to understand the result.
- Record the timestamp and timezone.
- Record the issue or state, including whether it is a detection, error, incomplete scan, cancellation, or unavailable capability.
- Preserve enough diagnostic context for investigation, while avoiding secrets and unrelated personal data.

## Required distinctions

Never label a skipped, failed, incomplete, cancelled, or unavailable scan as clear. A non-clear result is not automatically proof of malware; describe the actual finding or failure accurately.

## Privacy and integrity controls

- Apply access controls to detailed transcripts and investigation records.
- Minimise collection and retention to what is necessary for the security investigation.
- Protect records against unauthorised alteration.
- Define retention and deletion periods before implementation.
- Record timestamps consistently and do not silently rewrite historical timestamps.
- Verify that each platform's scan engine actually supplies the result being recorded.

## Acceptance criteria

- [ ] Verified-clear outcomes store only timestamp and verified-clear status.
- [ ] Non-clear outcomes retain relevant transcript/details, timestamp, and issue.
- [ ] Failed, skipped, incomplete, cancelled, and unavailable outcomes can never be mislabelled clear.
- [ ] Transcript contents are minimised and protected by access controls.
- [ ] Unit and platform tests cover each result state.
- [ ] Security/privacy review approves the policy before production use.

This document records a proposed policy only. It does not implement evidence collection or change current product behaviour.
