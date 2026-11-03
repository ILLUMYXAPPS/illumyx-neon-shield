# Neon Shield: Third-Party Components and Notices Register

**Record ID:** NS-IP-002  
**Project:** ILLUMYX Neon Shield  
**Repository:** `ILLUMYXAPPS/illumyx-neon-shield`  
**Record date:** 3 November 2026  
**Status:** Preliminary inventory; licence verification outstanding

## 1. Purpose

This register tracks software and other material that may carry rights belonging to third parties. It supports compliance with licence, attribution, source-disclosure, and notice obligations. It does not grant rights in those components to ILLUMYX.

## 2. Known starting inventory

The following direct Flutter dependencies are named in `mobile/pubspec.yaml` at the time this register was prepared:

| Component | Declared version constraint | Licence status in this register |
| --- | --- | --- |
| Flutter SDK | SDK dependency | Verify applicable Flutter/Dart notices |
| crypto | ^3.0.6 | Verify exact resolved version and licence |
| cryptography | ^2.7.0 | Verify exact resolved version and licence |
| file_picker | ^10.3.6 | Verify exact resolved version and licence |
| path_provider | ^2.1.5 | Verify exact resolved version and licence |
| device_info_plus | ^11.3.0 | Verify exact resolved version and licence |
| network_info_plus | ^6.1.3 | Verify exact resolved version and licence |
| package_info_plus | ^8.3.0 | Verify exact resolved version and licence |
| shared_preferences | ^2.5.3 | Verify exact resolved version and licence |
| http | ^1.2.2 | Verify exact resolved version and licence |
| flutter_secure_storage | ^9.2.4 | Verify exact resolved version and licence |
| flutter_test | Flutter SDK | Development dependency; verify SDK notices |
| flutter_lints | ^6.0.0 | Development dependency; verify exact resolved version and licence |

Version constraints are not exact resolved versions. The applicable lockfile and package metadata must be inspected before recording final versions or licence conclusions.

## 3. Required completion process

For every direct and transitive dependency, record:

- package/component name and exact resolved version;
- package source and upstream project;
- SPDX licence identifier and a copy or stable reference to the licence text;
- required copyright and attribution notices;
- whether source changes or bundled assets are included;
- whether the licence imposes source-disclosure, notice, attribution, patent, or redistribution conditions; and
- where the required notices are included in the distributed product.

Also inspect desktop Python dependencies, operating-system SDKs, build tools, fonts, icons, illustrations, templates, sample code, and any other externally sourced assets.

## 4. Distribution safeguards

- Keep third-party copyright notices intact.
- Include required licence texts and attribution notices in the appropriate distribution materials.
- Do not describe third-party components as exclusively owned by ILLUMYX.
- Do not remove or alter upstream notices unless the applicable licence permits it.
- Review licence compatibility before bundling or redistributing a component.
- Re-run the inventory when dependencies or build manifests change.

## 5. Current completion status

This is a preliminary register based on the direct dependencies visible in `mobile/pubspec.yaml`. It is not a complete software bill of materials and does not certify licence compliance. The lockfile-resolved direct and transitive inventory, desktop dependencies, and non-code assets remain to be completed.

**Related record:** `docs/OWNERSHIP_AND_DEVELOPMENT.md`.
