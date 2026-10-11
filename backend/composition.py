"""Application composition boundary for local and production runtimes."""
from __future__ import annotations

import os
from collections.abc import Callable

from backend.managed_store import ManagedAuthStore
from backend.observability import NoopSecurityEventSink, SecurityEventSink
from backend.production_config import ProductionConfig, validate_production_config
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
    """Build the service, requiring production storage to consume validated config."""
    if os.environ.get("NEON_AUTH_ENV") == "production":
        if secret_provider is None:
            raise RuntimeError("production requires an injected SecretProvider implementation")
        config = validate_production_config(secret_provider=secret_provider)
        if managed_store_factory is None:
            raise RuntimeError("production requires an injected ManagedAuthStore factory")
        if security_event_sink is None:
            raise RuntimeError("production requires an injected SecurityEventSink implementation")
        if security_alert_sink is None:
            raise RuntimeError("production requires an injected SecurityAlertSink implementation")

        # The factory receives the validated database URL and the exact deployment
        # pepper together. Deployment wiring must pass config.database_pepper to
        # ManagedDbAuthStore(pepper=...) and must not fetch a different env secret.
        managed_store = managed_store_factory(config)
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
