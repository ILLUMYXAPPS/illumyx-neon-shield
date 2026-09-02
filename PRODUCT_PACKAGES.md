# Neon Shield Product Packages

**Status:** Pre-release product definition  
**Owner:** ILLUMYX / Neon Shield  
**Last updated:** 2026-09-02

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
- Full supported-platform protection

### Premium Family

Everything in Premium, extended for a household.

- Everything in Premium
- Up to 5 family members
- Multiple devices per family member within the supported family entitlement
- Family-oriented device/account protection
- Full supported-platform protection across the family

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
7. Unknown or untrusted devices must not silently become trusted.
8. Security events must remain auditable where the applicable package provides audit history.
9. Product copy must not promise a capability that has not been implemented and verified.
10. Subscription state and feature entitlement must be kept separate from local presentation so entitlement enforcement cannot be bypassed by changing the client UI.

## Pre-release Verification Gates

Before public release, verify each package against the actual implementation:

- [ ] Free entitlement enforcement
- [ ] Premium entitlement enforcement
- [ ] Premium Family entitlement enforcement
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
