"""Application composition boundary for local and production runtimes."""
from __future__ import annotations

from backend.managed_store import ManagedAuthStore
from backend.production_config import validate_production_config
from backend.service import PersistentIdentityService
from backend.store import AuthStore


def build_service(*, managed_store: ManagedAuthStore | None = None) -> PersistentIdentityService:
    """Build the auth service without permitting a production SQLite fallback."""
    import os

    if os.environ.get("NEON_AUTH_ENV") == "production":
        validate_production_config()
        if managed_store is None:
            raise RuntimeError("production requires an injected ManagedAuthStore implementation")
        return PersistentIdentityService(managed_store)

    return PersistentIdentityService(AuthStore(os.environ.get("NEON_AUTH_DB", "neon_shield_auth.sqlite3")))
