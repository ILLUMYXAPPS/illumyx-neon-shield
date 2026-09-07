# Store contract hardening

The development SQLite `AuthStore` explicitly implements `ManagedAuthStore`.

This keeps the development adapter and production service contract aligned at runtime instead of relying only on structural type annotations.

This change does not make SQLite production storage. Production composition still requires an injected managed durable adapter and rejects a local SQLite fallback.
