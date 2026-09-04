# Neon Shield iOS TestFlight Runbook

## Purpose

This runbook is the final execution path for the signed iOS TestFlight gate. It is intentionally evidence-first: a green CI run is recorded, but the release gate only advances after the signed build and TestFlight path are actually verified.

## Current status

- Release-readiness estimate: **97%**
- Next gate: **98%**, real-world security behavior and signed iOS path verification
- iOS bundle ID: `com.illumyx.illumyx_neon_shield`
- Workflow: `.github/workflows/ios-testflight.yml`
- Latest iOS signing workflow hardening commit: `23b3b0ddcfbd75428a590fbd327bac3766f37ec7`

## GitHub Actions secrets

Create/populate these repository secrets in GitHub Actions. Never paste secret values into chat, issues, pull requests, logs, or source files.

| Secret | Source | Status |
|---|---|---|
| `ASC_KEY_ID` | App Store Connect Team Key ID | Ready: `MT9DU2939Y` |
| `ASC_ISSUER_ID` | App Store Connect API Issuer ID | Ready when copied from Apple |
| `ASC_PRIVATE_KEY_BASE64` | Base64 of the `.p8` private key | Pending local conversion |
| `APPLE_TEAM_ID` | Apple Developer Team ID | Pending confirmation from Apple Developer account |
| `IOS_DISTRIBUTION_CERT_BASE64` | Base64 of exported Apple Distribution `.p12` | Pending Mac |
| `IOS_CERT_PASSWORD` | Password protecting the `.p12` | Pending Mac export |
| `IOS_PROVISIONING_PROFILE_BASE64` | Base64 of matching provisioning profile | Pending Mac/Apple Developer setup |
| `IOS_KEYCHAIN_PASSWORD` | Temporary CI keychain password | Can be generated independently |

**Important:** The Apple membership number is not a substitute for `APPLE_TEAM_ID` unless Apple explicitly labels that value as the Team ID.

## Mac execution sequence

1. Open Keychain Access on the Mac.
2. Create a Certificate Signing Request with a private key.
3. In Apple Developer, create/download an **Apple Distribution** certificate using that CSR.
4. Import the certificate into Keychain Access and export the certificate plus private key as a password-protected `.p12`.
5. Create/download an iOS App Store provisioning profile for bundle ID `com.illumyx.illumyx_neon_shield` using the distribution certificate.
6. Verify the profile is intended for the correct team and bundle identifier.
7. Convert the `.p12` and provisioning profile to Base64 locally. Do not use an online converter.
8. Convert the App Store Connect `.p8` private key to Base64 locally.
9. Save the resulting values into the matching GitHub Actions secrets.
10. Run the **Neon Shield iOS TestFlight** workflow with `upload_to_testflight=true`.

## What the workflow verifies

Before building, CI verifies:

- required signing/upload inputs exist
- the generated project contains the expected bundle ID
- the provisioning profile decodes successfully
- profile TeamIdentifier matches `APPLE_TEAM_ID`
- profile application identifier matches `APPLE_TEAM_ID.com.illumyx.illumyx_neon_shield`
- Xcode project is configured for manual signing
- the configured provisioning profile is present in the export mapping
- Flutter tests pass

The signed build then verifies:

- an IPA is produced
- the IPA is non-empty
- the IPA is retained as a seven-day evidence artifact
- App Store Connect upload is attempted only when explicitly enabled
- temporary signing material is cleaned up after the job

## Evidence to record

For the successful run, record:

- workflow run number
- commit SHA
- iOS version/build number
- signed IPA artifact name
- App Store Connect processing result
- TestFlight availability
- device used for first real-device test: **iPhone 15 Pro**
- smoke-test evidence for the applicable `REAL_DEVICE_SMOKE_TEST.md` cases

Do not record passwords, private keys, authentication tokens, or raw device identifiers.

## Percentage rule

Do not move from 97% merely because the workflow starts or because unsigned CI is green.

Move to **98% only after the signed iOS/TestFlight gate and the required real-world evidence are genuinely verified.**

The project keeps failed runs and remediation history. No failed test is deleted to make the record look cleaner.

**Build → Test → Learn → Strengthen → Verify → Green light → Next green light.**
