# Atomic sign-in rate-limit hardening

The sign-in rate-limit decision and failure reservation must be performed atomically by the durable persistence layer. This prevents concurrent authentication requests from observing the same pre-threshold state and all proceeding before failures are recorded.
