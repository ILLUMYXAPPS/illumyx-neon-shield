# Security Policy

## Supported versions

Security reports should identify the affected release, build, or commit. Until a
formal support matrix is published, report suspected vulnerabilities affecting
the current development branch or any distributed Neon Shield release.

## Reporting a vulnerability

Please do not publish exploit details, credentials, private keys, personal
information, or unpatched vulnerability details in public issues or pull
requests.

If GitHub private vulnerability reporting is enabled for this repository, use
the repository Security tab and choose Report a vulnerability.

If private reporting is not available, contact the repository owner privately
through the ILLUMYXAPPS GitHub profile and request a secure channel for the
report. Include:
- A concise description of the suspected issue.
- The affected version, commit, platform, and configuration.
- Reproduction steps that do not expose real user data.
- The potential impact and any suggested mitigation.

Do not include passwords, signing certificates, private keys, access tokens, or
production user data in a report.

## Response and disclosure

The maintainers will acknowledge reports when practicable, investigate,
coordinate a fix, and agree on responsible disclosure timing with the reporter.
Please allow a reasonable opportunity to investigate and remediate before
public disclosure.

## Repository and signing credential safety

- Never commit Apple signing private keys, P12 exports, passwords, API keys,
  access tokens, provisioning secrets, or production credentials.
- Store release credentials only in approved, access-controlled secret stores.
- Revoke and rotate exposed credentials promptly.
- Report suspected unauthorised repository access or changes privately.
- Treat unexpected changes to the default branch, workflows, release assets,
  or signing configuration as security incidents requiring review.

## Scope

This policy covers ILLUMYX Neon Shield source code, build and release workflows,
project documentation, and official distribution assets. Third-party
dependencies remain subject to their own security policies and licences.
