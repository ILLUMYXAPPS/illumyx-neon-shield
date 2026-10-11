"""Application composition boundary for local and production runtimes."""
from __future__ import annotations

import os
from collections.abc import Callable

from backend.managed_store import ManagedAuthStore
from backend.observability import NoopSecurityEventSink, SecurityEventSink
from backend.production_config import ProductionConfig, validate_production_config
from backend.production_store_factory import build_managed_db_store
from backend.security_monitoring import NoopSecurityAlertSink, ProductionSecurityMonitor, SecurityAlertSink
from backend.secrets import SecretProvider
from backend.service import PersistentIdentityService
from backend.store import AuthStore


ManagedStoreFactory = Callable[[ProductionConfig], ManagedAuthStore]


def build_service(
    *,
    managed_store_factory: ManagedStoreFactory | None = None,
    security_event_sink: SecurityEventSink | None = None,
    security_alert_sink: SecurityAlertSink | None = None,
    secret_provider: SecretProvider | None = None,
) -> PersistentIdentityService:
    """Build the service; production defaults to the concrete managed PostgreSQL store."""
    if os.environ.get("NEON_AUTH_ENV") == "production":
        if secret_provider is None:
            raise RuntimeError("production requires an injected SecretProvider implementation")
        config = validate_production_config(secret_provider=secret_provider)
        if security_event_sink is None:
            raise RuntimeError("production requires an injected SecurityEventSink implementation")
        if security_alert_sink is None:
            raise RuntimeError("production requires an injected SecurityAlertSink implementation")

        # An explicit factory can be injected for deployment-specific testing, but
        # the safe default consumes the validated URL, DB credentials, and pepper.
        factory = managed_store_factory or build_managed_db_store
        managed_store = factory(config)
        if not isinstance(managed_store, ManagedAuthStore):
            raise RuntimeError("production ManagedAuthStore factory returned an invalid store")
        monitor = ProductionSecurityMonitor(
            security_event_sink,
            alert_sink=security_alert_sink,
        )
        return PersistentIdentityService(managed_store, security_event_sink=monitor)

    monitor = ProductionSecurityMonitor(
        security_event_sink or NoopSecurityEventSink(),
        alert_sink=security_alert_sink or NoopSecurityAlertSink(),
    )
    return PersistentIdentityService(
        AuthStore(os.environ.get("NEON_AUTH_DB", "neon_shield_auth.sqlite3")),
        security_event_sink=monitor,
    )
