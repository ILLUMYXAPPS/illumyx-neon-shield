# Timed Smart Scan Implementation Status

**Status: Desktop first slice implemented on a development branch; review and automated tests required. Not a malware scanner and not a production release.**

## What this change does

- Adds a local hourly scheduler for the existing read-only desktop security-posture checks.
- Prefers running after five minutes without interaction inside the Neon Shield window. This is an application-idle approximation, not a verified whole-device idle signal.
- If the app starts with an overdue scheduled check, asks the user before retrying.
- If a check becomes due while the app is active, asks whether to run now or defer for one hour.
- Allows the user to pause/resume the schedule and run checks manually.
- Stores schedule state and up to 100 recent evidence records locally in ~/.illumyx_neon_shield/smart_scan.json (the path is based on the user's home directory).
- Writes the JSON file atomically and attempts to restrict file permissions to the current user where the OS supports POSIX permissions.
- For verified-clear results, records only timestamp and verified_clear status. For non-clear or uncertain results, retains relevant supported security-check details and timestamp. Device inventory fields such as hostname are not added to scan evidence.

## What it does not do

- It does not scan files for malware, detect every threat, quarantine files, or replace Microsoft Defender or other operating-system protections.
- It does not guarantee exact hourly execution. The desktop app must be running for its in-app timer to execute.
- The five-minute idle preference reflects inactivity in the Neon Shield window, not reliable system-wide idle detection.
- It does not yet implement the mobile Flutter scheduler or native iOS/Android background scheduling.

## Next engineering steps

1. Run the Python unit-test matrix on Windows, macOS, and Linux.
2. Review persistence, missed-run behaviour, time changes, app shutdown, and error handling.
3. Add platform-specific idle/background adapters only where supported and tested.
4. Design and validate a genuine malware-detection integration before using the words malware scan or antivirus.
5. Implement the mobile path separately with platform-specific tests.
6. Complete security/privacy review and required release gates before merge or release.

This status file records the current development scope. It is not a claim of production readiness.
