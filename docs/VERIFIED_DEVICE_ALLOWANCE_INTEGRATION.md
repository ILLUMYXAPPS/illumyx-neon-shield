# Verified subscription device allowance integration

## What is connected

Device-pairing approval now resolves its allowance from the server's
`verified_subscriptions` records. The client cannot choose a package, account
owner, family membership, or device count.

The resolver runs on the same database cursor and transaction that changes the
pairing request to approved and inserts the trusted device. It locks the
verified subscription row (`FOR UPDATE` on managed databases); SQLite uses
its existing immediate write transaction. This serializes concurrent device
approvals against the same Premium account or Family household.

## Enforced paid-plan limits

- Premium: no more than 3 trusted devices for the account.
- Premium Family: no more than 2 trusted devices for each active family
  member, and no more than 10 trusted devices across the household.
- Free: unchanged. No new Free allowance has been assumed.

Expired, revoked, missing, or unrecognised subscription data never grants a
paid allowance. A family member inherits only the active verified Family
subscription belonging to the recorded household owner.

## Family membership data

Migration 7 creates `family_memberships`. The
`FamilyMembershipRepository` supports server-side activation after an
invitation has been accepted and removal by the household owner. It enforces
five people including the owner and prevents an account from being active in
two households or acting as both owner and member.

This PR does **not** implement the customer-facing invitation, acceptance,
or consent screens/API. Those must call the repository only after the invitee
has authenticated and accepted. Do not expose raw subject-ID membership writes
to clients.

## Deployment requirements

Apply production migrations through version 7 before enabling device pairing.
Production composition wires the resolver to the same managed database
connection factory used by auth and subscription persistence. If a production
runtime has no resolver, pairing initialization fails closed.

The Apple and Google provider credentials, product catalogue, notification
delivery, hosting, and live sandbox/production purchase checks remain separate
deployment gates. Passing automated tests does not establish live store
verification.

## Validation

Tests cover Premium's third/fourth-device boundary, expired/revoked fallback,
Family member inheritance, the per-member two-device cap, the household
ten-device cap, membership count and removal, and the pairing approval path
using a persisted verified subscription.
