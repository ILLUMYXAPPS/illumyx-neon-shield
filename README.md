# ILLUMYX NEON SHIELD v2 🛡️⚡

A lightweight, local-first defensive security posture dashboard written in Python.

## Current v2 features

- ILLUMYX Neon Shield desktop dashboard
- Device, operating-system, Python-runtime, and hostname information
- Available disk-space health check
- Local firewall-status reporting where the operating system exposes a supported command
- Microsoft Defender status reporting on Windows
- Clear **OK / REVIEW / INFO** states instead of exaggerated protection claims
- On-demand refresh with timestamp
- No remote scanning or credential collection

## How it works

`app_ui.py` provides the Tkinter interface. `security_checks.py` contains the local, read-only posture checks. The checks use Python's standard library and supported local operating-system commands where available.

Neon Shield treats an unavailable check as **INFO / Unknown** rather than assuming the device is safe or unsafe.

## Run

Python 3 with Tkinter is required.

```bash
python app_ui.py
```

## Privacy and safety

The current dashboard performs local checks only. It does not scan other devices, collect credentials, exploit systems, or transmit the displayed device information to a remote service.

## Next build targets

- Local report export
- Update/maintenance reminders
- More platform-specific health checks
- Guided remediation explanations
- Improved ILLUMYX visual polish and packaged desktop builds

## Project status

**v2 active development build**: functional local dashboard with modular posture checks, ready for desktop testing.
