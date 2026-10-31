# Intrusion Evidence Capture

## Scope and status
This component records security events observed by Neon Shield's own HTTP
server. It is not a packet sniffer, remote-device IP grabber, endpoint sensor,
scanner, or retaliation tool. The HTTP adapter integration is opt-in: capture
occurs only when an EvidenceStore is explicitly configured through
`NEON_EVIDENCE_DB`. It is currently a local SQLite implementation, not a
managed production evidence service.

## Capture rules
The HTTP adapter records failed authentication, rate limiting, malformed
requests, internal service errors, and unknown routes. It records UTC time,
event type, transport-derived source IP, method, path without query string,
status, and bounded user-agent. It never passes request bodies, credentials,
cookies, authorization headers, or full query strings to the evidence store.

Forwarded client IP headers are trusted only when the direct network peer is
inside an explicitly configured trusted proxy CIDR. Arbitrary
`X-Forwarded-For` headers are spoofable and ignored. Configure
`NEON_TRUSTED_PROXY_CIDRS` only with the exact CIDR ranges of proxies directly
trusted by the deployment.

## Integrity and handling
SQLite rows form a SHA-256 hash chain. `verify_chain` detects edits, deletion,
reordering, and broken links in the retained database. This is tamper-evident,
not tamper-proof: an administrator able to rewrite the entire database can
recompute the chain. For stronger preservation, periodically export and sign
the head hash to a separate access-controlled or immutable store, with trusted
time. An IP address is a technical lead, not proof of a person's identity.

Evidence storage errors are isolated from authentication responses. This
prevents an evidence-database outage from changing an auth response, but it
also means storage health must be monitored separately before production use.

## Before production activation
Use a managed encrypted evidence sink, least-privilege database access,
retention and deletion rules, privacy notice/legal review, access logs,
backup/restore tests, export controls, verified trusted-proxy CIDRs, operational
alerts, and independent security review. The local HTTP server binds only to
loopback and must remain behind a managed HTTPS edge.

## Tests
Run:
`python -m unittest tests.test_incident_evidence tests.test_http_evidence -v`
