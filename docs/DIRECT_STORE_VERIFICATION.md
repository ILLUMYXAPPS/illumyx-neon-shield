# Direct Apple and Google subscription verification

Status: Apple StoreKit 2 signed-transaction verification adapter added; Google Play live verification and store notification processing remain outstanding.

## Trust model

The authenticated Neon Shield server is the only authority that grants paid entitlements. Client-supplied tier names, purchase status, and local flags are untrusted. The server must verify purchase evidence with the relevant store, validate application/product/account identifiers, and persist the normalized result before entitlement policy can use it.

## Apple adapter requirements

Implemented in `store_verification.py`: `AppleStoreKitVerifier` verifies StoreKit 2 signed transaction JWS using Apple's official `SignedDataVerifier` for production and sandbox, enables online certificate checks by default, and rejects invalid signatures/certificate chains, mismatched bundle/product IDs, missing transaction IDs, and mismatched `appAccountToken`. It maps expiry and revocation facts into the common verified-purchase model. The adapter also exposes cryptographic verification of App Store Server Notifications V2 envelopes, but webhook routing, notification inner-payload processing, event reconciliation and App Store Server API subscription-status refresh are not yet wired. Provision Apple Root Certificates from Apple's PKI to the server, the production numeric App Store app ID, and the exact App Store Connect product IDs. The account binding must be supplied by the app as StoreKit's `appAccountToken` before purchase. Do not enable local testing/Xcode environments for customer entitlement decisions.

## Google Play adapter requirements

Use a server-held service account with the Google Play Developer API and purchase token. Validate Android application ID, product/base plan, purchase state, expiry, acknowledgement state, linked purchase token, and obfuscatedExternalAccountId binding. Authenticate real-time developer notifications and reconcile them against the Developer API.

## Current scaffold

store_verification.py defines normalized purchase request/result types, a product catalogue mapping, account-binding checks, and fail-closed defaults. Tests cover unconfigured providers, account mismatch, unknown products, wrong application IDs, revoked purchases, and expiry. The provider protocol is not itself a live Apple or Google integration.

## Remaining gates

1. Wire Apple App Store Server Notifications V2 webhook routing, nested signed transaction/renewal verification, and idempotent subscription reconciliation; add App Store Server API status/history refresh.
2. Implement Google Play Developer API verification.
3. Add authenticated, idempotent Google RTDN handling.
4. Configure store product IDs and app identifiers for each environment.
5. Store Apple private keys and Google service-account credentials only in server secret management.
6. Persist verified subscription state and notification event IDs durably.
7. Connect persisted snapshots to entitlement policy and atomic device-pairing enforcement.
8. Test race conditions and all four platform CI targets.

Locked limits: Premium 3 devices/account. Premium Family 5 members, 2 devices/member, 10 devices total. Pairing remains six-digit-code-only.

## Durable persistence foundation

Production migration 4 adds two server-side tables:

- `verified_subscriptions` stores the authenticated account, provider, application/product identifiers, package, environment, transaction references, a one-way hash of the purchase token, expiry, revocation state, and verification timestamps. The raw purchase token is not stored in this table.
- `store_notification_events` records provider event IDs, payload hashes, receipt/processing timestamps, and processing status. Its provider/event composite primary key provides the database uniqueness boundary needed for idempotent notification handling.

The migration is versioned and runs through the explicit production migration runner, not application startup. The schema is a persistence foundation only: no live Apple/Google cryptographic verification, notification authentication, event processor, subscription repository, or entitlement wiring is claimed complete by this change. Provider adapters must verify evidence before writing these records, and notification handlers must authenticate the provider before recording an event as trusted.

## Subscription persistence service

`backend/subscription_store.py` implements the DB-API repository for migration 4. It stores verified transaction facts, stores only a keyed hash of the purchase token, prevents a provider transaction from being reassigned to a different authenticated account, and returns a server-derived entitlement snapshot. Unknown, expired, or revoked subscriptions fall back to the Free package.

The repository also records authenticated notification event IDs with a unique provider/event key and supports a one-way transition from received to processed or rejected. Duplicate events are not inserted or re-finalized.

`StoreVerificationService.verify_and_persist` is the integration seam: it invokes the configured provider verifier, validates the server product mapping and account binding, persists the verified result, then returns the package snapshot. This remains fail-closed when live provider verifiers are absent.

**Security boundary:** `record_notification` is deliberately a persistence primitive, not a webhook endpoint. Callers must authenticate Apple's signed notification or Google's authenticated Pub/Sub delivery before recording the event. A production request handler, provider signature/API verification, durable account-binding issuance, and event-to-subscription reconciliation still need implementation.


## Server-issued account binding

Migration 5 adds `store_account_bindings`, with one unique opaque UUID per authenticated Neon Shield subject. `AccountBindingRepository.get_or_create` is the persistence primitive. `AuthenticatedStoreAccountBindingService.get_or_create_for_session` is the application boundary: it resolves the bearer session through the authoritative identity service, thereby applying session expiry, revocation, blocked-account and trusted-device checks, and passes only the resolved subject ID to the repository. The caller cannot supply a subject ID or choose the binding. Tests cover stable per-account issuance, distinct account bindings, unknown subjects, invalid/revoked sessions and untrusted devices. The stable UUID can be supplied to Apple's `appAccountToken` and Google's `obfuscatedExternalAccountId` when provider adapters are implemented. This is a server-side service boundary, not a deployed HTTP endpoint; production routing and managed identity/database adapters remain deployment integration work.


## Apple StoreKit 2 adapter implementation

`AppleStoreKitVerifier` uses Apple's official Python App Store Server Library. The
server-only dependency is declared in `requirements-server.txt` with a minimum
version of 3.1.2. This minimum is intentional: Apple published a security
advisory for stale OCSP response handling in versions through 3.1.1, and 3.1.2
contains the freshness fix. Production and sandbox verifiers are separate;
production requires the numeric App Store app ID. Online certificate checks
are enabled by default.

The adapter expects the StoreKit 2 signed transaction JWS as the purchase
evidence, not an unsigned client JSON object or the deprecated verifyReceipt
response. It validates Apple's JWS certificate chain and signature through the
official library, then checks the bundle ID, product ID and UUID
`appAccountToken` against the authenticated Neon Shield account binding.
Expiry and revocation are normalized before the existing product catalogue
maps the purchase to Premium or Premium Family. No real Apple keys, app ID,
root certificates or product IDs are embedded in the repository.

The adapter can also cryptographically verify a Notifications V2 signed
envelope. It does not yet expose a public notification endpoint or update
subscription state from notification events. Those steps remain a separate
server-side integration task. The official library's `verifyReceipt` legacy
path is not used.
