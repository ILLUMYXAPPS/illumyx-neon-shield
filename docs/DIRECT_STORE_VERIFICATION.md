# Direct Apple and Google subscription verification

Status: verification boundary scaffold added; live provider adapters and durable subscription persistence remain outstanding.

## Trust model

The authenticated Neon Shield server is the only authority that grants paid entitlements. Client-supplied tier names, purchase status, and local flags are untrusted. The server must verify purchase evidence with the relevant store, validate application/product/account identifiers, and persist the normalized result before entitlement policy can use it.

## Apple adapter requirements

Validate StoreKit 2 signed transaction data and/or App Store Server API responses, including signed payload chain, bundle ID, product ID, transaction and original transaction IDs, environment, expiry, refund/revocation, and appAccountToken binding. Authenticate App Store Server Notifications V2 and process renewals, billing retry/grace, expiry, refunds, and revocations idempotently.

## Google Play adapter requirements

Use a server-held service account with the Google Play Developer API and purchase token. Validate Android application ID, product/base plan, purchase state, expiry, acknowledgement state, linked purchase token, and obfuscatedExternalAccountId binding. Authenticate real-time developer notifications and reconcile them against the Developer API.

## Current scaffold

store_verification.py defines normalized purchase request/result types, a product catalogue mapping, account-binding checks, and fail-closed defaults. Tests cover unconfigured providers, account mismatch, unknown products, wrong application IDs, revoked purchases, and expiry. The provider protocol is not itself a live Apple or Google integration.

## Remaining gates

1. Implement Apple signed-transaction verification and App Store Server API calls.
2. Implement Google Play Developer API verification.
3. Add authenticated, idempotent notification handlers for both stores.
4. Configure store product IDs and app identifiers for each environment.
5. Store Apple private keys and Google service-account credentials only in server secret management.
6. Persist verified subscription state and notification event IDs durably.
7. Connect persisted snapshots to entitlement policy and atomic device-pairing enforcement.
8. Test race conditions and all four platform CI targets.

Locked limits: Premium 3 devices/account. Premium Family 5 members, 2 devices/member, 10 devices total. Pairing remains six-digit-code-only.
