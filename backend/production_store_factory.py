"""Concrete PostgreSQL factory for the production managed authentication store."""
from __future__ import annotations

from importlib import import_module
from urllib.parse import parse_qs, urlparse

from backend.managed_db_store import ManagedDbAuthStore
from backend.managed_store import ManagedAuthStore
from backend.production_config import ProductionConfig

_ALLOWED_SSLMODES = {"require", "verify-ca", "verify-full"}
_CONNECT_TIMEOUT_SECONDS = 10
_APPLICATION_NAME = "illumyx-neon-shield"


def _validate_config(config: ProductionConfig) -> None:
    if not isinstance(config, ProductionConfig):
        raise RuntimeError("production store factory requires validated ProductionConfig")
    if not config.database_user or config.database_user != config.database_user.strip():
        raise RuntimeError("production database user is missing or invalid")
    if not config.database_password or not config.database_password.strip():
        raise RuntimeError("production database password is missing")
    if not config.database_pepper or not config.database_pepper.strip():
        raise RuntimeError("production database pepper is missing")
    value = config.database_url
    if not value or value != value.strip() or any(ord(char) < 32 for char in value):
        raise RuntimeError("production database URL is missing or malformed")
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        _ = parsed.port
        sslmodes = parse_qs(parsed.query).get("sslmode", [])
    except ValueError as exc:
        raise RuntimeError("production database URL is malformed") from exc
    if parsed.scheme not in {"postgres", "postgresql"} or not hostname or not parsed.netloc:
        raise RuntimeError("production store requires a PostgreSQL URL with a valid host")
    if parsed.path in {"", "/"}:
        raise RuntimeError("production database URL must include a database name")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise RuntimeError("production database URL must not contain credentials or a fragment")
    if len(sslmodes) != 1 or sslmodes[0].lower() not in _ALLOWED_SSLMODES:
        raise RuntimeError("production database URL must explicitly enable TLS")


def build_managed_db_store(config: ProductionConfig) -> ManagedAuthStore:
    """Build a managed PostgreSQL store without connecting or running migrations.

    Credentials and the pepper are supplied separately from the URL. Connections
    are opened lazily per DB-API operation, use the URL's validated TLS settings,
    and have a bounded connection timeout. Schema migration remains an explicit
    deployment operation rather than an implicit application-startup side effect.
    """
    _validate_config(config)

    def connect():
        try:
            psycopg = import_module("psycopg")
        except ImportError as exc:
            raise RuntimeError(
                "production PostgreSQL support requires psycopg; install backend/requirements-production.txt"
            ) from exc
        return psycopg.connect(
            config.database_url,
            user=config.database_user,
            password=config.database_password,
            connect_timeout=_CONNECT_TIMEOUT_SECONDS,
            application_name=_APPLICATION_NAME,
        )

    store = ManagedDbAuthStore(
        connect,
        pepper=config.database_pepper,
        placeholder="%s",
        audit_lock_clause=" FOR UPDATE",
    )
    if not isinstance(store, ManagedAuthStore):
        raise RuntimeError("production PostgreSQL factory produced an invalid managed store")
    return store
