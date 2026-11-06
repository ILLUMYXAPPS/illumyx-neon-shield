# ILLUMYX Neon Shield mobile signing

This guide prepares the Android and iOS signing inputs used by the **Neon Shield Signed Mobile Release** workflow. Signing credentials must be stored only as GitHub Actions repository secrets. Never commit private keys, certificates, provisioning profiles, keystores, passwords, or service-account credentials.

## Current application identity

The signed workflow currently validates this application/bundle identifier for both platforms:

`com.illumyx.illumyxapp`

Keep this identifier consistent with the Apple Developer App ID and the Google Play application record. Do not change it casually after store registration, because store identity and upgrade continuity depend on it.

## Android signing

Required GitHub Actions repository secrets:

- `ANDROID_KEYSTORE_BASE64`: base64-encoded Android upload keystore (`.jks`)
- `ANDROID_KEYSTORE_PASSWORD`: keystore password
- `ANDROID_KEY_ALIAS`: upload-key alias
- `ANDROID_KEY_PASSWORD`: key password

The workflow produces a signed Android App Bundle (`.aab`). Before store distribution, establish the matching Google Play Console application and confirm the upload-key arrangement. The Android keystore can be prepared independently of Apple signing; keep a secure offline backup of the keystore and its credentials.

## Apple iOS signing

Required GitHub Actions repository secrets:

- `IOS_DISTRIBUTION_CERT_BASE64`: base64-encoded Apple Distribution `.p12`
- `IOS_CERT_PASSWORD`: password protecting the `.p12`
- `IOS_PROVISIONING_PROFILE_BASE64`: base64-encoded App Store provisioning profile
- `IOS_KEYCHAIN_PASSWORD`: unique temporary CI keychain password
- `APPLE_TEAM_ID`: Apple Developer Team ID

Before creating these secrets:

1. Confirm that the Apple Developer Program membership is active and identify the correct Team ID.
2. Confirm that the explicit App ID uses `com.illumyx.illumyxapp`.
3. Create an Apple Distribution certificate and export its private key and certificate together as a password-protected `.p12` file.
4. Create an App Store provisioning profile for the matching App ID and distribution certificate.
5. Base64-encode the `.p12` and provisioning profile locally, then add the resulting values to the named GitHub Actions secrets.
6. Generate a separate strong random value for `IOS_KEYCHAIN_PASSWORD`. Do not reuse the certificate password.
7. Never paste credentials, private keys, certificate files, provisioning profiles, or their encoded contents into chat, issues, pull requests, or source control.

A Mac with Keychain Access/Xcode is the normal way to create the certificate signing request and export the Apple Distribution `.p12`. If purchasing a Mac is not currently practical, the code review, Android preparation, Apple account/App ID checks, and documentation work can still proceed. The Apple certificate-export step can wait until a trusted Mac is available; do not send signing material to an untrusted third party.

## Running a signed build

Open GitHub Actions and manually run **Neon Shield Signed Mobile Release**. Supply the version name and a monotonically increasing build number. The workflow runs Android and iOS jobs independently. The iOS job uses a GitHub-hosted macOS runner, so a personally owned Mac is not required to execute the CI signing build once valid Apple signing inputs have been securely prepared.

A successful signed CI build is not the same as physical-device validation, TestFlight acceptance, App Store approval, or release authorization. Keep those gates separate.

## Desktop signing

The Windows and macOS desktop beta workflow currently creates unsigned beta artifacts. Windows code signing, macOS Developer ID signing/notarization, installer packaging, update delivery, and physical desktop testing are separate release tasks. Mobile signing secrets do not sign desktop applications.
