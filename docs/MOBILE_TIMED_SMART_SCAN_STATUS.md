# Mobile Timed Smart Scan: Implementation Status

**Status: Mobile hourly posture-review reminder implemented as an early Flutter beta slice. Not a background scanner and not a release-ready security feature.**

## Implemented

- Hourly reminder schedule state persisted locally with SharedPreferences.
- Reminder is enabled by default and can be paused or resumed in the dashboard.
- The in-app reminder checks while Neon Shield is open and waits for five minutes without pointer interaction before prompting.
- If a reminder is overdue, the app asks the user whether to review now or be asked later.
- A user can acknowledge that they reviewed the available posture dashboard.
- Evidence minimization: the reminder stores a timestamp and the explicit status `review_acknowledged_not_verified`. It never claims `verified_clear`, because the current mobile beta does not expose a verified security-check engine.
- Unit tests cover schedule defaults, pause behavior, review acknowledgement and next-due scheduling.

## Platform limitations

- iOS and Android may suspend or terminate the app, so this in-app timer cannot promise exact hourly execution and does not run when the app is closed or suspended.
- Native background scheduling, notification permissions, Android WorkManager integration, iOS BGTaskScheduler integration and physical-device validation are not included in this change.
- The current mobile beta's posture dashboard reports device/platform/network and local setup information. It does not perform malware scanning, threat blocking or verified security posture checks.
- This feature is therefore labelled a **posture-review reminder**, not a functioning mobile malware scan.

## Next steps before production

1. Run Flutter format, analyze and tests in CI.
2. Validate on representative physical iOS and Android devices.
3. Decide whether to add native background scheduling; document that operating systems still control execution timing.
4. Implement platform-supported security checks and define their verified outcomes before enabling any `verified_clear` evidence state.
5. Review permission prompts, notification behavior, lifecycle transitions, time changes, persistence failures and privacy.
6. Keep the change in a draft pull request until review and all release gates are complete.
