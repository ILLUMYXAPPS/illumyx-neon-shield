# Universal device pairing

## Status

Implementation is underway on `feature/universal-device-pairing`. The current increment adds backend pairing persistence and endpoints, Flutter manual-code pairing, and connected-device management. QR presentation/scanning, subscription device-limit enforcement, production deployment, and independent review remain outstanding. This is not production-ready.

## Customer experience

- One Neon Shield account is used across the customer's authorised devices.
- A new device starts a pairing request and displays a short-lived six-digit code plus a QR representation of the same pairing request.
- The customer approves the request from a device that already has a valid, server-verified session.
- The request expires after five minutes and can be completed only once.
- The customer can view, rename, and unlink devices from **My Connected Devices**.
- Revoking a device must invalidate its existing sessions and prevent refresh or new sign-in.
- Pairing another device to the same account is distinct from inviting a family member. Family members require separate identities/profiles and privacy boundaries.

## Security contract

1. The server is authoritative. Local preferences, client flags, and a successful QR scan never grant trust by themselves.
2. Pairing requests use a cryptographically random, high-entropy secret. Store only a keyed hash of the secret; never store or log the raw secret or six-digit display code.
3. The six-digit code is a lookup aid, not the sole security credential. Apply strict per-account, per-device, and per-IP attempt limits; constant-time secret comparison; and generic failure responses.
4. The QR payload carries an opaque, single-use pairing secret and a versioned scheme identifier. It must not contain account credentials, session tokens, personal data, or a reusable device identifier.
5. Only an already authenticated and currently trusted session belonging to the target account can approve a pending request.
6. A successful approval atomically consumes the request and adds the new device to the trusted-device registry. Replays, expired requests, revoked approvers, and cross-account approvals fail closed.
7. New-device status polling returns only pending/approved/expired/rejected state and is rate limited. It must not reveal account existence or device inventory.
8. Device identifiers and pairing secrets are stored as keyed hashes. Device display names are bounded, validated customer labels; raw identifiers are never returned in the inventory API.
9. Unlinking a device revokes its sessions and trust in one transaction and writes a privacy-safe audit event.
10. All endpoints require HTTPS outside loopback development.

## Initial API contract

- POST /v1/device-pairing/start: new device submits account credentials, stable device identifier, and a display name. Server verifies credentials and creates a five-minute pending request without trusting the new device.
- POST /v1/device-pairing/approve: existing trusted session submits the one-time pairing secret or scanned QR payload. Server verifies account ownership and consumes the request atomically.
- POST /v1/device-pairing/status: new device polls using the one-time request handle and secret in the request body. Keeping the secret out of the URL reduces exposure in proxy and access logs. Response is limited to pending, approved, expired, or rejected.
- GET /v1/devices: authenticated session lists the account's authorised devices, with safe display metadata only.
- PATCH /v1/devices/{device_ref}: authenticated session renames a device after ownership validation.
- DELETE /v1/devices/{device_ref}: authenticated session unlinks a different device and revokes its sessions. Require recent authentication or equivalent step-up verification before unlinking the current device or all devices.

The final route shapes may be adapted to existing API conventions, but the security properties above are acceptance requirements.

## Entitlements and family boundary

- Device limits must be checked by the server against the current subscription entitlement, never enforced only in Flutter.
- Premium and Family device/member limits remain configurable policy values until the product owner approves exact numbers. Do not invent or hard-code a commercial limit in this feature.
- Family invitations and family-member profiles are a separate workflow. A family member must not see another member's devices, account identity, files, or security history unless explicitly shared through a defined permission model.

## Delivery sequence

1. Backend persistence, pairing challenge lifecycle, atomic approval, revocation, audit events, and abuse controls.
2. Backend API and contract tests, including expiry, replay, brute-force throttling, cross-account attempts, concurrent approvals, and revoked approvers.
3. Flutter API contracts, a manual-code pairing screen, approval from an existing trusted device, and a **My Connected Devices** screen for rename/unlink.
4. QR rendering/scanning, platform permission handling, and an accessible fallback. QR payload support exists at the API boundary; the current mobile screen uses the manual code.
5. Enforce approved Premium/Family device limits through the server-side entitlement service. Exact limits remain a product decision and are not hard-coded.
6. Complete CI validation on Windows, macOS, Android, and iOS; then independent review and physical-device validation.

## Release boundaries

The current implementation hashes pairing secrets and six-digit codes with the deployment pepper, expires requests after five minutes, caps approval attempts at five per request, verifies the approving session server-side, consumes approval once, and revokes a device's sessions when it is unlinked. IP-based throttling, subscription entitlement/device-limit enforcement, step-up authentication for sensitive device management, QR presentation/scanning, and a managed-production deployment migration still need work. A green unit-test or simulator build does not prove production pairing works. Production HTTPS, managed persistence, real account/entitlement integration, physical-device validation, and independent security review remain separate gates. Do not merge this feature or describe it as production-ready until those gates are met.