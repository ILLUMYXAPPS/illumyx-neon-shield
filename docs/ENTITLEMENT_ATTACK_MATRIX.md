# Neon Shield Entitlement Attack Matrix

**Status:** Pre-release verification artifact  
**Branch:** `build/entitlement-attack-matrix`

## Purpose

This matrix defines the security cases required before Free, Premium, and Premium Family entitlements can be marked production-ready.

The server is authoritative. Client presentation must never grant an entitlement that the service does not authorize.

## Required cases

| ID | Scenario | Expected result | Evidence required |
|---|---|---|---|
| ENT-01 | Free user requests Premium capability | DENY | Automated test + server response |
| ENT-02 | Valid Premium user requests Premium capability | ALLOW | Automated test |
| ENT-03 | Valid Premium Family user requests Premium capability | ALLOW | Automated test |
| ENT-04 | Family member 1-5 is authorized | ALLOW | Service-level test |
| ENT-05 | Family member 6 is added | DENY | Service-level test |
| ENT-06 | Premium subscription expires | Premium capability DENY | Lifecycle test |
| ENT-07 | Premium subscription is cancelled | Premium capability DENY | Lifecycle test |
| ENT-08 | Valid renewal restores Premium | ALLOW | Lifecycle test |
| ENT-09 | Premium upgrade activates entitlement | ALLOW | Upgrade test |
| ENT-10 | Premium downgrade removes Premium capability | DENY | Downgrade test |
| ENT-11 | Client locally changes package state | Server remains authoritative | Integration/security test |
| ENT-12 | Unknown device attempts authentication | DENY + AUDIT | Existing auth test/evidence |
| ENT-13 | Trusted device becomes untrusted | DENY + AUDIT | Existing auth regression |
| ENT-14 | Expired session requests protected operation | DENY | Session lifecycle test |
| ENT-15 | Revoked session requests protected operation | DENY | Session lifecycle test |
| ENT-16 | Blocked identity requests access | DENY + AUDIT | Authentication test |

## Release rule

No entitlement gate may be marked green from UI inspection alone. Each protected capability must have server-side enforcement and automated evidence where applicable.

## Current implementation evidence

The current authentication reference implementation already rejects untrusted devices during sign-in, records an audit event, re-checks trust during refresh, and validates active sessions. See `auth_server.py`.

Commercial package enforcement remains an open release gate until the cases above are implemented and verified against the actual subscription service.

## CI compatibility note

GitHub Actions is moving fully away from Node 20, with Node 24 becoming the default and Node 20 removal scheduled for September 23, 2026. Keep workflow actions on Node-24-compatible releases while this test campaign is added.
