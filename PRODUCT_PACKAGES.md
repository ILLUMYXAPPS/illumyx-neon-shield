# Neon Shield Product Packages

**Status:** Pre-release product definition  
**Owner:** ILLUMYX / Neon Shield  
**Last updated:** 2026-11-07

## Purpose

This document is the single product-level reference for the customer packages planned for Neon Shield. It defines which capabilities belong to Free, Premium, and Premium Family, while distinguishing planned entitlements from features already verified in the beta codebase.

> **Important:** A feature listed as planned or gated is not considered production-ready until the corresponding implementation and entitlement enforcement have been verified.

## Packages

### Free

Core privacy and security posture features intended to let a customer understand the security state of their own devices.

- Core privacy/security posture dashboard
- Device and operating-system awareness
- Basic supported firewall/status checks
- Supported Microsoft Defender status reporting on Windows
- OK / REVIEW / INFO guidance
- Local refresh/checks
- Local report export
- Basic security/device awareness
- Essential security notifications

### Premium

Everything in Free, plus advanced account and device protection.

- Everything in Free
- Trusted-device management
- Advanced unknown/untrusted-device protection
- Login/device security alerts
- Security/audit history
- Advanced account protection
- Enhanced device-login controls
- Expanded multi-device protection
- **Up to 3 linked devices per account**, allowing a phone, tablet, and desktop
- Full supported-platform protection

### Premium Family

Everything in Premium, extended for a household.

- Everything in Premium
- Up to 5 family members
- **Up to 2 linked devices per family member**
- **10 linked devices maximum across the family**
- Family-oriented device/account protection
- Full supported-platform protection across the family

## Device allowance policy (approved 2026-11-07)

The following limits are approved product requirements:

| Package | Account/member allowance | Device limit |
|---|---:|---:|
| Free | 1 account | Existing Free allowance; not changed by this decision |
| Premium | 1 account holder | 3 linked devices |
| Premium Family | Up to 5 members | 2 linked devices per member |
| Premium Family total | Up to 5 members | 10 linked devices maximum |

Enforcement requirements:

1. The server is authoritative for device counts. Client-side counters or UI checks are not sufficient.
2. A device is counted against the authenticated account or the specific Family member who owns its membership.
3. A Premium account cannot link a fourth active device.
4. A Family member cannot link a third active device, even when another member has unused capacity.
5. A Family household cannot exceed 10 active linked devices in total.
6. Device unlinking/revocation must release that device's allowance after the server confirms the change.
7. Pending, expired, rejected, or revoked pairing requests must not consume an active-device slot indefinitely.
8. Concurrent pairing approvals must be handled atomically so two approvals cannot exceed a limit.
9. Account changes, Family removal, subscription expiry, and downgrade must be handled by explicit server-side lifecycle rules. Do not silently delete customer data or trust a client-reported subscription state.
10. Device limits apply across supported platforms: Windows, macOS, iOS, and Android.

The Premium allowance is three devices because customers may reasonably use a phone, tablet, and desktop. Family capacity is five separate member profiles, with two devices allocated to each member, for a household maximum of ten.

## Entitlement Matrix

| Capability | Free | Premium | Premium Family |
|---|:---:|:---:|:---:|
| Core security posture dashboard | YES | YES | YES |
| Device / OS awareness | YES | YES | YES |
| Local read-only security checks | YES | YES | YES |
| Firewall status where supported | YES | YES | YES |
| Microsoft Defender status on Windows | YES | YES | YES |
| OK / REVIEW / INFO guidance | YES | YES | YES |
| Local report export | YES | YES | YES |
| Basic device awareness | YES | YES | YES |
| Essential security alerts | YES | YES | YES |
| Trusted-device management | NO | YES | YES |
| Advanced unknown-device protection | NO | YES | YES |
| Login/device security alerts | NO | YES | YES |
| Security/audit history | BASIC | FULL | FULL |
| Advanced account protection | NO | YES | YES |
| Enhanced device-login controls | NO | YES | YES |
| Expanded multi-device protection | NO | YES | YES |
| Family members | 1 | 1 | UP TO 5 |
| Linked devices | Existing Free allowance | UP TO 3 | UP TO 2 PER MEMBER; 10 TOTAL |
| Cross-platform protection | CORE | FULL | FULL |

## Subscription Pricing Plan

Pricing below is the current product plan and must be kept consistent across product documentation, purchase screens, and public pricing material.

### Premium

- Introductory: **$49.99 AUD/year**
- Planned standard: **$69.99 AUD/year**
- Introductory monthly: **$5.99 AUD/month**
- Introductory weekly: **$1.99 AUD/week**

### Premium Family

- Introductory: **$79.99 AUD/year**
- Planned standard: **$99.99 AUD/year**
- Coverage: **up to 5 family members**

## Entitlement Rules

1. Free users must never receive Premium-only capabilities through a UI-only check.
2. Premium users receive Free + Premium entitlements while their subscription is valid.
3. Premium Family users receive Free + Premium + Family entitlements while their subscription is valid.
4. Upgrade must activate the newly purchased entitlements predictably.
5. Downgrade, expiry, cancellation, and renewal behaviour must be explicitly handled and tested.
6. Family membership limits must be enforced by the service, not only displayed by the client.
7. **Premium's three-device limit and Premium Family's two-devices-per-member / ten-devices-total limits must be enforced by the server-side device-pairing and entitlement services.**
8. Unknown or untrusted devices must not silently become trusted.
9. Security events must remain auditable where the applicable package provides audit history.
10. Product copy must not promise a capability that has not been implemented and verified.
11. Subscription state and feature entitlement must be kept separate from local presentation so entitlement enforcement cannot be bypassed by changing the client UI.

## Pre-release Verification Gates

Before public release, verify each package against the actual implementation:

- [ ] Free entitlement enforcement
- [ ] Premium entitlement enforcement
- [ ] Premium Family entitlement enforcement
- [ ] Premium maximum of 3 active linked devices
- [ ] Family maximum of 2 active linked devices per member
- [ ] Family maximum of 10 active linked devices in total
- [ ] Concurrent pairing cannot exceed device limits
- [ ] Unlink/revoke releases the correct device slot
- [ ] Family member removal and subscription lifecycle behaviour
- [ ] Upgrade flow
- [ ] Downgrade flow
- [ ] Subscription expiry/cancellation behaviour
- [ ] Renewal behaviour
- [ ] Family member limit enforcement
- [ ] Trusted-device enforcement
- [ ] Unknown/untrusted-device denial and audit behaviour
- [ ] Login/device security alert behaviour
- [ ] Customer-facing pricing matches this document
- [ ] Customer-facing feature lists match this document
- [ ] Backend and mobile entitlement checks agree
- [ ] Production database configured
- [ ] Production secret management configured
- [ ] HTTPS production deployment verified
- [ ] Real-device authentication testing completed
- [ ] External security review completed

## Current Beta Boundary

The repository README currently describes Neon Shield as beta software and documents local, read-only security posture checks. The README also states that mobile signed distribution remains dependent on valid Android and Apple signing credentials and that representative physical-device testing is required before stable release.

This package document therefore defines the **commercial/product target**. It does not by itself certify every Premium or Family feature as implemented.

## Release Principle

**No public package promise without a matching, tested entitlement.**

The goal is a clear customer experience: customers should know exactly what they receive, the application should enforce exactly that entitlement, and the CEO/product documentation should remain aligned with both.
