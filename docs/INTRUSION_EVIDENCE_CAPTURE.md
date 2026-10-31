# Intrusion Evidence Capture

## Scope and status
This component stores security events observed by Neon Shield's own server.
It is not a packet sniffer, remote-device IP grabber, endpoint sensor, scanner,
or retaliation tool. It is opt-in and is NOT wired into production request
handling until the actual server entry point and trusted proxy topology are
confirmed.

## Capture rules
Call EvidenceStore.record_event only after a server-side security handler
classifies an event (failed authentication, authorization denial, rate limit,
invalid signature, or confirmed abuse rule). Record UTC time, event type,
transport-derived source IP, method, path without query string, status, bounded
user-agent, and minimal scalar details. Never record request bodies, passwords,
tokens, cookies, authorization headers, or full query strings.

Forwarded client IP headers are trusted only when the direct network peer is
inside an explicitly configured trusted proxy CIDR. Arbitrary X-Forwarded-For
headers are spoofable and must be ignored.

## Integrity and handling
SQLite rows form a SHA-256 hash chain. verify_chain detects edits, deletion,
reordering, and broken links in the retained database. This is tamper-evident,
not tamper-proof: an administrator able to rewrite the entire DB can recompute
the chain. For stronger preservation, periodically export and sign the head
hash to a separate access-controlled or immutable store, with trusted time.
An IP address is a technical lead, not proof of a person's identity.

Before activation: configure least-privilege DB access, retention and deletion,
privacy notice/legal review, access logs, backups, export controls, trusted
proxy CIDRs, production integration tests and operational alerts.

Run tests: python -m unittest tests.test_incident_evidence -v
