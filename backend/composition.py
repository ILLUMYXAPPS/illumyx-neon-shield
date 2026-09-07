"""Application composition boundary for local and production runtimes."""
from __future__ import annotations

import os

from backend.managed_store import ManagedAuthStore
from backend.observability import NoopSecurityEventSink, SecurityEventSink
from backend.production_config import validate_production_config
from backend.service import PersistentIdentityService
from backend.store import AuthStore


def build_service(
    *,
    managed_store: ManagedAuthStore | None = None,
    security_event_sink: SecurityEventSink | None = None,
) -> PersistentIdentityService:
    """Build auth service without permitting production monitoring or SQLite fallbacks."""
    if os.environ.get("NEON_AUTH_ENV") == "production":
        validate_production_config()
        if managed_store is None:
            raise RuntimeError("production requires an injected ManagedAuthStore implementation")
        if security_event_sink is None:
            raise RuntimeError("production requires an injected SecurityEventSink implementation")
        return PersistentIdentityService(managed_store, security_event_sink=security_event_sink)

    return PersistentIdentityService(
        AuthStore(os.environ.get("NEON_AUTH_DB", "neon_shield_auth.sqlite3")),
        security_event_sink=security_event_sink or NoopSecurityEventSink(),
    )
