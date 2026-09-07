# Security Audit Note

This file records the rationale for the production session-resolution audit fix.

The production HTTP adapter resolves bearer sessions through `IdentityService.resolve_session()`. `PersistentIdentityService` implemented the underlying session validation path but did not expose the required `resolve_session()` method, leaving protected HTTP endpoints unable to resolve valid production sessions.

The fix delegates `resolve_session()` to the same server-authoritative validation path used by refresh and revocation, preserving expiry, revocation, identity-block and trusted-device checks.

No Apple signing, provisioning, TestFlight, certificates, iOS release configuration, or App Store configuration is changed by this audit fix.
