# Neon Shield Release Readiness

This checklist separates work that can safely continue before certification from production gates that must remain controlled.

## Mobile experience

- [x] First-run onboarding shell
- [x] Returning-user bootstrap path
- [x] Existing owner setup is respected
- [x] Bootstrap failure does not grant dashboard access
- [x] Back/forward onboarding navigation coverage
- [x] Protection Command Centre posture summary surfaces known local security state
- [ ] Wire profile selection to the existing protection-profile contract
- [ ] Add end-to-end authentication and device-verification coverage against the HTTPS backend

## Security and backend

- [x] Server-authoritative authentication foundation
- [x] Trusted-device enforcement remains server-authoritative
- [x] Session refresh/revocation remains server-authoritative
- [ ] Managed production database configured
- [ ] Production authentication pepper/secret store configured
- [ ] HTTPS production deployment verified
- [ ] External security review completed

## Mobile release

- [ ] Apple distribution/signing configuration verified in the release environment
- [ ] Android release signing configuration verified in the release environment
- [ ] Store metadata, privacy disclosures, and support information completed
- [ ] Production endpoint configuration verified
- [ ] Release build smoke-tested on supported iOS and Android devices

## Certification guardrails

Do not bypass or weaken authentication, trusted-device enforcement, cryptographic boundaries, server-side policy, signing controls, or production secrets to make certification progress appear green.

A green CI result means the repository checks passed. It does not by itself certify the security architecture or store-readiness of the product.

## CI trigger verification

This marker is intentionally documentation-only. It exists to verify that pushes to the feature branch trigger the configured CI workflows without changing application or security behavior.
