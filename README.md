# ILLUMYX NEON SHIELD v2 🛡️⚡

A lightweight, local-first defensive security posture dashboard written in Python.

## Current v2 features

- ILLUMYX Neon Shield desktop dashboard
- Device, operating-system, Python-runtime, and hostname information
- Available disk-space health check
- Local firewall-status reporting where the operating system exposes a supported command
- Microsoft Defender status reporting on Windows
- Clear **OK / REVIEW / INFO** states instead of exaggerated protection claims
- Guided recommendations for each reported result
- Exportable local text reports containing results, details, and recommended next steps
- On-demand refresh with timestamp
- Defensive error handling so unavailable checks do not crash the dashboard
- No remote scanning or credential collection

## How it works

`app_ui.py` provides the Tkinter interface. `security_checks.py` contains the local, read-only posture checks. The checks use Python's standard library and supported local operating-system commands where available.

Neon Shield treats an unavailable check as **INFO / Unknown** rather than assuming the device is safe or unsafe. Selecting a result in the dashboard shows a suggested next step. The **Export report** button saves the current results to a local text file chosen by the user.

## Run

Python 3 with Tkinter is required.

```bash
python app_ui.py
```

## Privacy and safety

The current dashboard performs local checks only. It does not scan other devices, collect credentials, exploit systems, or transmit the displayed device information to a remote service. Exported reports are written only to the local path selected by the user.

## Next build targets

- Update and maintenance reminders
- More platform-specific health checks
- Improved ILLUMYX visual polish
- Packaged desktop builds for easier launching
- Automated tests for the check engine

## Project status

**v2 active development build**: functional local dashboard with modular posture checks, guided recommendations, and report export, ready for desktop testing.
