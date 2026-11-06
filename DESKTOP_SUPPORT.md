# ILLUMYX Neon Shield desktop validation

Windows and macOS are added as desktop build targets for the Flutter application.

## CI build approach

The Windows and macOS runner projects are generated during their respective GitHub Actions jobs with Flutter's platform generator. This follows the existing Android and iOS build pattern in `.github/workflows/mobile-build.yml`, which also generates native platform projects during CI rather than storing generated platform directories in the repository.

Each desktop job:

1. Runs on the matching hosted operating system.
2. Generates only its requested Flutter desktop platform.
3. Resolves Flutter dependencies.
4. Runs static analysis and the Flutter test suite.
5. Builds a release-mode desktop beta.
6. Uploads the build output as a workflow artifact.

## Important boundaries

- These are unsigned CI beta builds, not store-ready installers.
- A successful hosted build is not a substitute for testing on representative physical Windows PCs and Macs.
- macOS distribution signing, notarization, Windows installer packaging, update delivery, and platform-specific security review remain separate work.
- Desktop support must not weaken authentication, encrypted vault, secure-storage, or fail-closed behaviour.
- A platform-specific plugin failure must be fixed or explicitly documented. Do not silently replace secure storage with an insecure fallback.
- The dashboard reports local posture only. It does not provide antivirus scanning, threat blocking, or active file protection.

## Current scope

The dashboard now identifies Windows and macOS devices through `device_info_plus`. The desktop jobs exercise the existing app, plugin registrations, static analysis, tests, and native builds. Further desktop-specific UX, permissions, accessibility, and security review remain necessary before any desktop release decision.
