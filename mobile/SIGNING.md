# ILLUMYX Neon Shield mobile signing

The signed mobile workflow reads signing material only from GitHub Actions secrets. Do not commit private keys, certificates, provisioning profiles, passwords, or service-account credentials to the repository.

## Android

Required repository secrets:

- `ANDROID_KEYSTORE_BASE64`: base64-encoded Android upload keystore (`.jks`)
- `ANDROID_KEYSTORE_PASSWORD`: keystore password
- `ANDROID_KEY_ALIAS`: upload-key alias
- `ANDROID_KEY_PASSWORD`: key password

The workflow produces a signed Android App Bundle (`.aab`) suitable for upload to Google Play once the Play Console app and signing configuration are established.

## Apple iOS

Required repository secrets:

- `IOS_DISTRIBUTION_CERT_BASE64`: base64-encoded Apple Distribution `.p12`
- `IOS_CERT_PASSWORD`: password protecting the `.p12`
- `IOS_PROVISIONING_PROFILE_BASE64`: base64-encoded App Store provisioning profile
- `IOS_KEYCHAIN_PASSWORD`: random temporary CI keychain password
- `APPLE_TEAM_ID`: Apple Developer Team ID

The workflow produces a signed `.ipa` when the certificate, provisioning profile, bundle identifier, and Apple team all match. The IPA can then be submitted through App Store Connect/TestFlight using an authenticated Apple distribution process.

## Bundle identity

Neon Shield's intended mobile application ID is `com.illumyx.illumyxapp`. The Android beta, signed Android release, signed iOS release, and TestFlight workflows must all generate and validate this same ID.

Before running a signed release, confirm that this exact ID is registered or available in the relevant Google Play Console and Apple Developer/App Store Connect accounts. Bundle IDs should be treated as release identity, not casually changed after store registration. Do not create or upload signing material until the registered IDs and signing assets are confirmed.

## Running a signed build

Open GitHub Actions and manually run **Neon Shield Signed Mobile Release**. Supply the version name and monotonically increasing build number. The Android and iOS jobs are independent, so a problem with one platform does not require exposing the other platform's signing material.
