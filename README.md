# ILLUMYX NEON SHIELD

ILLUMYX Neon Shield is a local-first security posture dashboard for desktop
and mobile devices. The desktop application is written in Python with Tkinter;
the mobile beta is built with Flutter.

> **Beta software:** Neon Shield reports defensive posture information. It is
> not antivirus software, does not guarantee protection, and does not replace
> operating-system updates or professional security review.

## Desktop v2.0 beta

- Device, operating-system, Python-runtime, hostname, and disk-space reporting
- Local firewall-status checks where the operating system exposes a supported command
- Microsoft Defender status reporting on Windows
- Clear **OK / REVIEW / INFO** states with guided recommendations
- Local text-report export and on-demand refresh
- Defensive failure handling for unavailable checks
- Automated tests on Windows, macOS, and Linux
- Packaged Windows and macOS beta releases

Run from source with Python 3 and Tkinter:

```bash
python app_ui.py
```

Run the desktop test suite:

```bash
python -m unittest discover -s tests -v
```

## Mobile v1.0 beta

The `mobile/` directory contains the Flutter application and smoke test.

```bash
cd mobile
flutter pub get
flutter analyze
flutter test
```

Unsigned beta builds run without store credentials. Signed Android and iOS
distribution requires repository secrets documented in `mobile/SIGNING.md`.
Signing keys, certificates, provisioning profiles, passwords, and credentials
must never be committed to the repository.

## Privacy and safety

Neon Shield performs local, read-only checks. It does not scan remote devices,
collect credentials, exploit systems, or transmit displayed device information
to a remote service. Exported reports are written only to the path selected by
the user.

## Release status

- Desktop: `v2.0-beta` release available for Windows and macOS
- Mobile: Flutter beta implemented; signed distribution remains dependent on
  valid Android and Apple signing credentials

Platform-specific behaviour should be tested on representative physical
devices before any stable release.

## License

Copyright (c) 2025-2026 Aaron Paszek / ILLUMYX. All rights reserved.

This is proprietary software. No permission is granted to copy, modify,
redistribute, sublicense, or create derivative works without prior written
authorization. See `LICENSE` for the complete terms.
