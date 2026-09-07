# Security Audit Note

This file records the rationale for removing the unused `NEON_SESSION_SECRET` production secret.

`PersistentIdentityService` uses opaque, random, server-side session tokens that are persisted as hashes and rotated atomically. The service does not sign, encrypt, or otherwise derive session credentials from `NEON_SESSION_SECRET`.

Requiring a secret that has no cryptographic consumer increases deployment secret surface without adding a security property. The secret has therefore been removed from the production configuration contract until a concrete cryptographic use is implemented and tested.

This change does not alter Apple signing, provisioning, TestFlight, certificates, iOS release configuration, or App Store configuration.
