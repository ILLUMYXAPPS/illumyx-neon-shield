# Neon Shield macOS Endpoint Security extension

This directory contains the observation-only native boundary for macOS Endpoint Security.

Apple's Endpoint Security framework provides system-event monitoring and requires the
`com.apple.developer.endpoint-security.client` entitlement. Neon Shield intentionally
uses only `ES_EVENT_TYPE_NOTIFY_EXEC` and `ES_EVENT_TYPE_NOTIFY_FORK` in this first stage.

## Integration requirements

1. Add `NeonEndpointClient.c` to a macOS System Extension target.
2. Apply `NeonEndpointExtension.entitlements` to that target.
3. Obtain Apple's Endpoint Security entitlement approval for the distribution target.
4. Sign and install the System Extension through the normal System Extensions flow.
5. Replace the temporary stdout transport with a signed, local IPC mechanism between
the extension and the Neon Shield host application.
6. Normalize received events into the Neon Forensics schema and run them through the
existing deny-by-default field policy before persistence.

## Safety boundary

The extension is notification-only. It does not authorize operations, block processes,
modify firewall rules, inspect file contents, collect keystrokes, or collect credentials.
The host must not expand the subscribed event set without a corresponding privacy and
policy review.

## Distribution note

The entitlement is not granted merely by adding the plist key. Apple's documentation
requires the Endpoint Security client entitlement and the target must be correctly
signed for distribution. Test on a representative physical Mac before release.
