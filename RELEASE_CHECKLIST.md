# Prerelease Verification Checklist

- [ ] CI workflow runs on the release candidate PR
- [ ] Python 3.10 and 3.12 test matrix is green
- [ ] macOS, Ubuntu, and Windows jobs are green
- [ ] Exact-match fixture passes
- [ ] Strong-partial-match fixture passes
- [ ] Lyrics-only fixture passes
- [ ] Metadata-only fixture passes without being treated as strong proof
- [ ] False-positive fixture passes
- [ ] Match transcript preserves score and evidence
- [ ] Review decision is recorded in the audit trail
- [ ] Security/access regression suite is green
- [ ] Final smoke test passes
- [ ] Prerelease package/version is generated
