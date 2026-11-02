# Neon Shield Smart Scanning Ecosystem

> **Status: PROPOSED DESIGN ONLY. Not implemented, tested, or verified.**
>
> This document records the proposed product architecture and configuration. It does not assert that scheduled scanning, malware detection, background execution, or cross-platform parity currently exists.

**Project:** ILLUMYX Neon Shield  
**Design record:** 22 October 2026  
**Scope:** Architecture proposal and implementation acceptance criteria

## 1. Goals

- Define a platform-aware design for scheduled Smart Scanning.
- Keep the user in control of scheduling and missed-run decisions.
- Avoid claiming security capabilities that have not been implemented and validated.
- Keep the proposal outside the protected `main` release branch until reviewed and explicitly approved.

## 2. Proposed scanning defaults

| Setting | Proposed value |
|---|---|
| Frequency | Every hour (target cadence, not a guaranteed execution interval) |
| Preferred timing | When the device is idle and platform rules permit |
| Scan mode | Smart Scan, limited to verified checks available on that platform |
| Missed scan behaviour | Ask the user before retrying |
| Battery policy | Defer intensive work when battery is low or the device is under resource pressure |
| Duplicate handling | Do not start a second scan while an equivalent scan is already running |
| Manual control | Keep an explicit user-initiated scan path where supported |
| Status reporting | Distinguish completed, delayed, skipped, failed, cancelled, and unavailable states |

## 3. Proposed software ecosystem

### User interface
Dashboard, Scanner, Alerts, Activity, and Settings surfaces. Display the selected schedule, last scan status, next eligible opportunity when it can be estimated, and any user decision needed.

### Protection orchestrator
Coordinates scan requests, permissions, task lifecycle, user consent, cancellation, and error handling. It must not report success before the underlying operation confirms success.

### Scan scheduler
Evaluates whether a scan is due, checks platform eligibility and idle preference, avoids duplicate work, and applies missed-run behaviour. The hourly interval is a scheduling target only; operating-system policies may delay or prevent background execution.

### Smart Scan engine
Invokes only real, documented, platform-supported checks. “Smart Scan” must not be presented as malware detection unless a suitable detection engine exists and has passed validation. An unavailable scanner must be shown as unavailable, not as a clean result.

### Resource manager
Applies battery, power-source, workload, thermal/resource and user-activity safeguards where the platform exposes reliable signals. Deferrals must be visible in scan history.

### Security event log
Records relevant scan lifecycle events: scheduled, started, completed, skipped, deferred, cancelled, failed, and user retry choice. Minimise collected data, protect logs with appropriate access controls, and define retention before implementation. Do not log secrets or unnecessary file contents.

### Platform integration layer
Uses native, documented scheduling, permission, notification, and security interfaces. Platform-specific adapters must report their actual capabilities rather than pretending that every platform supports the same background behaviour.

## 4. Platform constraints

| Platform | Design considerations |
|---|---|
| Windows | Use supported background scheduling and permissions. Verify the actual scan engine and any required security integrations. |
| macOS | Respect privacy permissions, background execution limits, file-access restrictions, and supported security APIs. |
| iOS | Background execution is system-controlled. Exact hourly scans cannot be guaranteed; use only approved background mechanisms and provide foreground/manual alternatives where needed. |
| Android | Background execution depends on OS scheduling, battery optimisation, permissions, and potentially manufacturer-specific restrictions. Exact hourly scans cannot be guaranteed. |

## 5. Battery and workload rules

1. Defer intensive scans when battery is low, especially when not connected to power.
2. Prefer idle periods but do not assume every platform exposes a reliable, identical idle signal.
3. Allow the operating system to delay, batch, or suspend background work.
4. Prevent overlapping duplicate scans and provide safe cancellation.
5. Show the user when a scan was delayed, skipped, unavailable, or could not complete.
6. Treat hourly timing as best effort, never as a security guarantee.
7. Provide an accessible way to review and change scan preferences.

## 6. Missed-scan workflow

1. Detect and record that the planned run did not execute, when this can be determined reliably.
2. When the application can execute and notifications or UI are available, ask whether the user wants to retry.
3. If the user accepts, re-check platform eligibility, permissions, battery policy, and duplicate-task state before starting.
4. If the user declines, record the choice and wait for the next eligible scheduled opportunity.
5. If prompting is not possible while the app is suspended, retain a pending decision and surface it the next time the app is active. Do not claim a prompt was delivered when it was not.

## 7. Acceptance criteria before implementation can be marked complete

- [ ] Scheduling preferences persist securely and survive an application restart.
- [ ] Scheduler handles clock changes, app restarts, permissions being revoked, and unavailable background execution.
- [ ] Idle preference is implemented and tested separately for each supported platform.
- [ ] Missed-run prompt appears when execution and notification/UI conditions permit; pending prompts are surfaced later.
- [ ] Low-battery and resource safeguards are tested without silently dropping scan state.
- [ ] Duplicate scan prevention and cancellation are tested.
- [ ] Event history correctly distinguishes success, failure, skip, deferral, cancellation, and unavailable engine.
- [ ] Smart Scan results correspond to real, documented checks; no unsupported malware-detection claims.
- [ ] Windows, macOS, iOS, and Android behaviour is tested separately on supported environments/devices.
- [ ] Privacy, retention, permission handling, and security-event access controls receive review.
- [ ] CI and relevant tests pass; evidence is attached to the implementation change.
- [ ] Independent human security review and release-readiness gates are completed before production certification.

## 8. Release and governance note

This document is a design proposal only. Adding this file does not implement or enable timed scanning. Do not merge it into `main`, mark the feature complete, or advertise the feature as available until the proposal is reviewed, implementation is completed on a separate change, platform-specific tests pass, and required security/release approvals are obtained.

The project’s existing release-control principle remains in force: repository checks alone are not proof of production readiness.
