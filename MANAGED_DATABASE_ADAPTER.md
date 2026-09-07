# Managed database adapter

Neon Shield now has an explicit persistence boundary for production.

`backend/store.py` remains the SQLite development/integration adapter. It must
not be exposed as the production database. Production code must provide a
managed durable implementation of `backend.managed_store.ManagedAuthStore`.

## Required guarantees

The production adapter must preserve the existing server-authoritative
`PersistentIdentityService` behaviour:

- credential records remain hashed and are never stored as plaintext
- identities, trusted devices, blocked identities/phones, sessions and audit
  events are durable across process restarts
- session tokens are stored only as hashes
- device identifiers are stored only as hashes/fingerprints where the contract
  permits
- session revocation and refresh rotation are atomic enough that an old token
  cannot be reused after successful rotation
- audit-chain writes preserve `previous_hash` ordering and integrity
- database failures fail closed rather than granting access
- all database operations use parameterized queries or an ORM with equivalent
  parameter binding
- backups, encryption at rest, access control and retention are configured by
  the managed database platform before production launch

## Adapter boundary

The production implementation should be dependency-injected into the
authentication service. Do not fork authentication policy between storage
implementations. The service remains responsible for authentication and
authorization decisions; the adapter is responsible for durable persistence.

No cloud provider, database credentials, network endpoint, or production data
is provisioned by this change.
