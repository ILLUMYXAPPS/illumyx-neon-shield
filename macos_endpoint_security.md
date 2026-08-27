# macOS Endpoint Security integration

Neon Shield should use Apple's Endpoint Security framework for future native macOS telemetry rather than attempting kernel extensions or private APIs.

Apple documents Endpoint Security as the supported C API for monitoring potentially malicious system events, including process execution and filesystem activity. A system extension packaged with the app requires the `com.apple.developer.endpoint-security.client` entitlement. See Apple's official Endpoint Security documentation before implementation.

## Phase 1 scope

Use **NOTIFY** events only. Do not authorize or deny operations in the first integration.

Collect only:

- event timestamp
- event type
- process identifier
- parent process identifier
- executable path where appropriate
- signing identity / code-signing status where available
- event outcome

Do not collect command-line secrets, credentials, private document contents, or unrelated application data.

## Phase 2

After entitlement, signing, packaging and privacy review are complete, add selected filesystem/process notifications. Authorization events must remain disabled unless a specific prevention feature is designed, reviewed and explicitly disclosed.
