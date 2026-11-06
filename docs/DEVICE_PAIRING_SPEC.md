# Universal device pairing

## Status

Implementation is underway on `feature/universal-device-pairing`. The agreed customer flow is six-digit code pairing only. QR display, camera scanning, and camera permissions are deliberately out of scope. Subscription device-limit enforcement, production deployment, and independent review remain outstanding. This is not production-ready.

## Customer experience

- One Neon Shield account is used across the customer's authorised devices.
- A new device starts a pairing request and displays a six-digit code and a request reference.
- The customer opens **My Connected Devices** on a device already signed in to the same Neon Shield account, selects **Approve a Device**, and enters the request reference and six-digit code.
- The server verifies the account, code, expiry, and approval attempt limit before trusting the new device.
- The request expires after five minutes and can be completed only once.
- The customer can view, rename, and unlink devices from **My Connected Devices**.
- Revoking a device must invalidate its existing sessions and prevent refresh or new sign-in.
- Pairing another device to the same account is distinct from inviting a family member. Family members require separate identities/profiles and privacy boundaries.

## Security contract

1. The server is authoritative. Local preferences and client flags never grant trust by themselves.
2. Generate the six-digit code with a cryptographically secure random generator. Store only a keyed hash of the code; never store or log the raw code.
3. The request reference identifies the pending challenge but is not a credential. Approval requires the six-digit code and a currently trusted session belonging to the target account.
4. Expire requests after five minutes, permit no more than five failed code attempts per request, compare hashes in constant time, and return generic failure responses.
5. A successful approval atomically consumes the request and adds the new device to the trusted-device registry. Replays, expired requests, revoked approvers, and cross-account approvals fail closed.
6. New-device status polling uses a separate high-entropy secret in the request body, never in the URL. Store only a keyed hash of this polling secret. It must not be accepted as an approval credential.
7. Status polling returns only pending/approved/expired/rejected state and must not reveal account existence or device inventory. Production deployment must apply edge-level rate limiting; application-level polling throttling remains outstanding.
8. Device identifiers and polling secrets are stored as keyed hashes. Device display names are bounded, validated customer labels; raw identifiers are never returned in the inventory API.
9. Unlinking a device revokes its sessions and trust in one transaction and writes a privacy-safe audit event.
10. All endpoints require HTTPS outside loopback development.

## Initial API contract

- POST /v1/device-pairing/start: new device submits account credentials, stable device identifier, and a display name. Server verifies credentials and creates a five-minute pending request without trusting the new device. Response includes request_id, six-digit pairing_code, a separate polling secret, expiry, and poll interval.
- POST /v1/device-pairing/approve: existing trusted session submits request_id and the six-digit pairing_code. Server verifies account ownership and consumes the request atomically.
- POST /v1/device-pairing/status: new device polls using the request handle and separate polling secret in the request body. Keeping the secret out of the URL reduces exposure in proxy and access logs. Response is limited to pending, approved, expired, or rejected.
- GET /v1/devices: authenticated session lists the account's authorised devices, with safe display metadata only.
- PATCH /v1/devices/{device_ref}: authenticated session renames a device after ownership validation.
- DELETE /v1/devices/{device_ref}: authenticated session unlinks a different device and revokes its sessions. Require recent authentication or equivalent step-up verification before unlinking the current device or all devices.

The final route shapes may be adapted to existing API conventions, but the security properties above are acceptance requirements.

## Entitlements and family boundary

- Device limits must be checked by the server against the current subscription entitlement, never enforced only in Flutter.
- Premium and Family device/member limits remain configurable policy values until the product owner approves exact numbers. Do not invent or hard-code a commercial limit in this feature.
- Family invitations and family-member profiles are a separate workflow. A family member must not see another member's devices, account identity, files, or security history unless explicitly shared through a defined permission model.

## Delivery sequence

1. Backend persistence, six-digit challenge lifecycle, atomic code approval, revocation, audit events, and abuse controls.
2. Backend API and contract tests, including expiry, replay, brute-force throttling, cross-account attempts, concurrent approvals, and revoked approvers.
3. Flutter API contracts, a manual six-digit pairing screen, approval from an existing trusted device, and a **My Connected Devices** screen for rename/unlink.
4. Enforce approved Premium/Family device limits through the server-side entitlement service. Exact limits remain a product decision and are not hard-coded.
5. Complete CI validation on Windows, macOS, Android, and iOS; then independent review and physical-device validation.

## Release boundaries

The current implementation hashes the six-digit approval code and separate polling secret with the deployment pepper, expires requests after five minutes, caps approval attempts at five per request, verifies the approving session server-side, consumes approval once, and revokes a device's sessions when it is unlinked. IP/edge throttling, application-level polling throttling, subscription entitlement/device-limit enforcement, step-up authentication for sensitive device management, and a managed-production deployment migration still need work. A green unit-test or simulator build does not prove production pairing works. Production HTTPS, managed persistence, real account/entitlement integration, physical-device validation, and independent security review remain separate gates. Do not merge this feature or describe it as production-ready until those gates are met.
