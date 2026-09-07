# Distributed sign-in rate-limit hardening

Neon Shield sign-in abuse protection now persists failed-attempt state through `ManagedAuthStore` rather than keeping the limiter only in process memory.

## Security properties

- Identity keys are stored as peppered SHA-256 hashes, never plaintext identities.
- The failure window is persisted with its start timestamp.
- The threshold is bounded by `max_sign_ins`.
- Expired windows reset atomically.
- Successful authentication clears the identity's failure state.
- Managed DB updates use the same row-lock strategy as other security-critical state, with `FOR UPDATE` as the production default.
- SQLite integration uses a transaction lock for the same state transition.
- No limiter state is kept solely in process memory, so multiple application instances share the same enforcement state.

## Production migration

Migration version `3`, `create_sign_in_rate_limits`, creates the durable rate-limit table. Production deployment must apply the reviewed `PRODUCTION_MIGRATIONS` set before starting instances that use this contract.

The application does not run migrations automatically at startup.

## Boundary

This hardening covers per-identity failed sign-in throttling. It does not replace edge/WAF/IP reputation controls, credential-stuffing detection, CAPTCHA/challenge policy, or provider-side identity protections. Those remain complementary deployment controls.

No Apple signing, provisioning, TestFlight, certificate, iOS release, or App Store configuration is changed by this hardening.
