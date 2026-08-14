# Neon Shield hardening bundle

Prepared for `ILLUMYXAPPS/illumyx-neon-shield` at main commit `6e07838`.

## Confirmed CI root cause

The failed signed mobile run stopped before compilation:

- Android failed in **Restore Android signing key** because the required
  keystore secret was empty or unavailable.
- iOS failed in **Install Apple signing certificate** because the required
  distribution-certificate secret was empty or unavailable.

The replacement workflow reports every missing secret by name, validates the
decoded Android keystore, allows Android and iOS to be selected independently,
and runs analysis/tests before packaging.

## Included replacements

- Proprietary `LICENSE` and copyright `NOTICE`
- Updated `README.md` and mobile signing instructions
- Defensive `.gitignore` for signing material and generated outputs
- Corrected desktop `requirements.txt`
- Updated signed mobile, mobile build, mobile checks, and Python lint workflows
- `CLEANUP.md` with conservative deletion targets

## Required repository-side configuration

Code cannot supply private signing credentials. Add the required values as
GitHub Actions repository secrets using `mobile/SIGNING.md`; then dispatch only
the platform whose credentials are ready.

## Suggested branch and verification

Create a branch such as `maintenance/release-hardening`, copy the replacement
files to the repository root, perform the deletions in `CLEANUP.md`, and run:

```bash
python -m compileall -q app_ui.py security_checks.py tests
python -m unittest discover -s tests -v
```

If Flutter is installed, also run:

```bash
cd mobile
flutter pub get
flutter analyze
flutter test
```
