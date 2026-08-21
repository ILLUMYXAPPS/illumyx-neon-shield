# Repository cleanup manifest

Apply the replacement files in this bundle, then remove the following obsolete
root files from the repository:

- `app_ui 2.py` — duplicate placeholder UI
- `app_ui 3.py` — identical duplicate placeholder UI
- `app_ui.zip` — generated archive; releases/artifacts should carry archives
- `encrypt_pricing.py` — unrelated pricing experiment that creates a local key
- `main.py` — obsolete placeholder launcher
- `RunMe.sh` and `RunMe.bat` — launch the obsolete `main.py`
- `build.sh` and `build.bat` — obsolete `YourApp` build scripts referencing a
  missing `assets/icon.ico`

`app_cli.py` is maintained and must not be deleted. It provides the current
copyright online-sweep CLI entry point.

The PNG and SVG design/status assets are not referenced by the maintained app,
build specification, or README. They have been left out of automatic deletion
because they may be retained intentionally as brand source material. Review
them separately before removal.

Do not delete `app_ui.py`, `security_checks.py`, `NeonShield.spec`, `tests/`,
`mobile/`, or the current GitHub workflows.
