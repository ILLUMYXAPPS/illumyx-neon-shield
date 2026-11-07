"""Application composition boundary for local and production runtimes."""
from __future__ import annotations

import os

from backend.account_binding import AccountBindingRepository, AuthenticatedStoreAccountBindingService
from backend.managed_db_store import ManagedDbAuthStore
from backend.managed_store import ManagedAuthStore
from backend.observability import NoopSecurityEventSink, SecurityEventSink
from backend.production_config import validate_production_config
from backend.security_monitoring import NoopSecurityAlertSink, ProductionSecurityMonitor, SecurityAlertSink
from backend.secrets import EnvironmentSecretProvider, SecretProvider
from backend.service import PersistentIdentityService
from backend.subscription_store import StoreSubscriptionRepository
from backend.store import AuthStore


def build_service(
    *,
    managed_store: ManagedAuthStore | None = None,
    security_event_sink: SecurityEventSink | None = None,
    security_alert_sink: SecurityAlertSink | None = None,
    secret_provider: SecretProvider | None = None,
    account_binding_repository: AccountBindingRepository | None = None,
    database_connection_factory=None,
    database_placeholder: str = "%s",
    store_verification_service=None,
    subscription_repository: StoreSubscriptionRepository | None = None,
) -> PersistentIdentityService:
    """Build auth service without permitting production secret, storage, or monitoring fallbacks."""
    if os.environ.get("NEON_AUTH_ENV") == "production":
        if secret_provider is None:
            raise RuntimeError("production requires an injected SecretProvider implementation")
        config = validate_production_config(secret_provider=secret_provider)
        if managed_store is None and database_connection_factory is None:
            raise RuntimeError("production requires an injected ManagedAuthStore or database connection factory")
        if managed_store is None:
            managed_store = ManagedDbAuthStore(
                database_connection_factory,
                pepper=config.database_pepper,
                placeholder=database_placeholder,
            )
        if account_binding_repository is None and database_connection_factory is not None:
            account_binding_repository = AccountBindingRepository(
                database_connection_factory,
                placeholder=database_placeholder,
            )
        if subscription_repository is None and database_connection_factory is not None:
            subscription_repository = StoreSubscriptionRepository(
                database_connection_factory,
                pepper=config.database_pepper,
                placeholder=database_placeholder,
            )
        if security_event_sink is None:
            raise RuntimeError("production requires an injected SecurityEventSink implementation")
        if security_alert_sink is None:
            raise RuntimeError("production requires an injected SecurityAlertSink implementation")
        if account_binding_repository is None:
            raise RuntimeError("production requires an injected durable AccountBindingRepository implementation")
        monitor = ProductionSecurityMonitor(
            security_event_sink,
            alert_sink=security_alert_sink,
        )
        service = PersistentIdentityService(managed_store, security_event_sink=monitor)
        service.store_account_binding_service = AuthenticatedStoreAccountBindingService(
            service, account_binding_repository
        )
        service.store_verification_service = store_verification_service
        service.store_subscription_repository = subscription_repository
        return service

    monitor = ProductionSecurityMonitor(
        security_event_sink or NoopSecurityEventSink(),
        alert_sink=security_alert_sink or NoopSecurityAlertSink(),
    )
    service = PersistentIdentityService(
        AuthStore(os.environ.get("NEON_AUTH_DB", "neon_shield_auth.sqlite3")),
        security_event_sink=monitor,
    )
    if account_binding_repository is not None:
        service.store_account_binding_service = AuthenticatedStoreAccountBindingService(
            service, account_binding_repository
        )
    service.store_verification_service = store_verification_service
    service.store_subscription_repository = subscription_repository
    return service
