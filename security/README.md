# Neon Shield Security Layer

This directory contains local-first security primitives used by Neon Shield.

## Access-control foundation

`access_control.py` provides:

- one-time owner initialization
- constant-time owner verification
- owner-authorized trusted-device changes
- immutable-in-process ownership initialization
- audit events for security-sensitive actions
- cryptographically secure bootstrap-secret generation

## Integration rule

The access-control policy must remain behind an application boundary. UI code must not directly mutate ownership or trusted-device state.

Remote ownership replacement is intentionally not supported by this foundation.

## Next integration boundary

The mobile application should expose security state through a dedicated service/repository layer rather than embedding policy decisions in widgets.
