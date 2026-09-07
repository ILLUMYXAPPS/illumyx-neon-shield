"""Application composition boundary for local and production runtimes."""
from __future__ import annotations

import os

from backend.managed_store import ManagedAuthStore
from backend.observability import NoopSecurityEventSink, SecurityEventSink
from backend.production_config import validate_production_config
from backend.security_monitoring import NoopSecurityAlertSink, ProductionSecurityMonitor, SecurityAlertSink
from backend.secrets import EnvironmentSecretProvider, SecretProvider
from backend.service import PersistentIdentityService
from backend.store import AuthStore


def build_service(
    *,
    managed_store: ManagedAuthStore | None = None,
    security_event_sink: SecurityEventSink | None = None,
    security_alert_sink: SecurityAlertSink | None = None,
    secret_provider: SecretProvider | None = None,
) -> PersistentIdentityService:
    """Build auth service without permitting production secret, storage, or monitoring fallbacks."""
    if os.environ.get("NEON_AUTH_ENV") == "production":
        if secret_provider is None:
            raise RuntimeError("production requires an injected SecretProvider implementation")
        validate_production_config(secret_provider=secret_provider)
        if managed_store is None:
            raise RuntimeError("production requires an injected ManagedAuthStore implementation")
        if security_event_sink is None:
            raise RuntimeError("production requires an injected SecurityEventSink implementation")
        if security_alert_sink is None:
            raise RuntimeError("production requires an injected SecurityAlertSink implementation")
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
