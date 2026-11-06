"""Fail-closed production configuration validation."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from backend.secrets import SecretProvider

_REQUIRED = (
    "NEON_AUTH_DB",
    "NEON_DB_USER",
    "NEON_IDP_URL",
    "NEON_IDP_CLIENT_ID",
    "NEON_MONITORING_ENDPOINT",
)
_REQUIRED_SECRETS = ("NEON_IDP_CLIENT_SECRET", "NEON_DB_PASSWORD", "NEON_DB_PEPPER")
_ALLOWED_DB_SSLMODES = {"require", "verify-ca", "verify-full"}


@dataclass(frozen=True)
class ProductionConfig:
    database_url: str
    database_user: str
    database_password: str = field(repr=False)
    idp_url: str
    idp_client_id: str
    idp_client_secret: str = field(repr=False)
    database_pepper: str = field(repr=False)
    monitoring_endpoint: str = ""


@dataclass(frozen=True)
class MigrationConfig:
    """Minimal configuration required by the standalone schema migration job."""
    database_url: str
    database_user: str
    database_password: str = field(repr=False)


def _require_https(name: str, value: str) -> None:
    if not value or value != value.strip() or any(ord(char) < 32 for char in value):
        raise RuntimeError(f"{name} must be an absolute HTTPS URL without surrounding whitespace or control characters")
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a valid absolute HTTPS URL") from exc
    if parsed.scheme != "https" or not parsed.netloc or not hostname:
        raise RuntimeError(f"{name} must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError(f"{name} must not contain embedded credentials")
    if parsed.fragment:
        raise RuntimeError(f"{name} must not contain a URL fragment")


def _reject_local_database(value: str) -> None:
    lowered = value.lower()
    if lowered.startswith(("sqlite:", "sqlite3:", "file:")) or lowered in {":memory:", "memory"}:
        raise RuntimeError("NEON_AUTH_DB must identify a managed durable production database")


def _require_database_tls(value: str) -> None:
    """Require a valid PostgreSQL URL with explicit TLS and no embedded credentials."""
    if not value or value != value.strip() or any(ord(char) < 32 for char in value):
        raise RuntimeError("NEON_AUTH_DB must be a valid PostgreSQL connection URL")
    try:
        parsed = urlparse(value)
        sslmodes = parse_qs(parsed.query).get("sslmode", [])
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise RuntimeError("NEON_AUTH_DB must be a valid PostgreSQL connection URL") from exc
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.netloc or not hostname:
        raise RuntimeError("NEON_AUTH_DB must use a PostgreSQL connection URL with a valid host and port")
    if parsed.path in {"", "/"}:
        raise RuntimeError("NEON_AUTH_DB must include a database name in the connection URL")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError("NEON_AUTH_DB must not contain embedded credentials; use NEON_DB_USER and NEON_DB_PASSWORD")
    if parsed.fragment:
        raise RuntimeError("NEON_AUTH_DB must not contain a URL fragment")
    if len(sslmodes) != 1 or sslmodes[0].lower() not in _ALLOWED_DB_SSLMODES:
        raise RuntimeError(
            "NEON_AUTH_DB must explicitly require TLS with sslmode=require, verify-ca, or verify-full"
        )


def _validate_database_user(database_user: str) -> None:
    if not database_user.strip() or database_user != database_user.strip() or any(ord(c) < 32 for c in database_user):
        raise RuntimeError("NEON_DB_USER must be non-empty and must not have surrounding whitespace or control characters")


def validate_migration_config(
    env: dict[str, str] | None = None,
    *,
    secret_provider: SecretProvider,
) -> MigrationConfig:
    """Validate only the production database settings needed by migration deployment."""
    values = os.environ if env is None else env
    if values.get("NEON_AUTH_ENV") != "production":
        raise RuntimeError("production configuration requires NEON_AUTH_ENV=production")
    missing = [name for name in ("NEON_AUTH_DB", "NEON_DB_USER") if not values.get(name)]
    if missing:
        raise RuntimeError("missing migration configuration: " + ", ".join(missing))
    if secret_provider is None:
        raise RuntimeError("migration configuration requires an injected SecretProvider")

    database_url = values["NEON_AUTH_DB"]
    database_user = values["NEON_DB_USER"]
    _reject_local_database(database_url)
    _require_database_tls(database_url)
    _validate_database_user(database_user)
    database_password = secret_provider.get_required("NEON_DB_PASSWORD")
    return MigrationConfig(
        database_url=database_url,
        database_user=database_user,
        database_password=database_password,
    )


def validate_production_config(
    env: dict[str, str] | None = None,
    *,
    secret_provider: SecretProvider,
) -> ProductionConfig:
    """Validate full application production configuration and resolve secrets."""
    values = os.environ if env is None else env
    if values.get("NEON_AUTH_ENV") != "production":
        raise RuntimeError("production configuration requires NEON_AUTH_ENV=production")
    missing = [name for name in _REQUIRED if not values.get(name)]
    if missing:
        raise RuntimeError("missing production configuration: " + ", ".join(missing))
    if secret_provider is None:
        raise RuntimeError("production configuration requires an injected SecretProvider")

    database_url = values["NEON_AUTH_DB"]
    database_user = values["NEON_DB_USER"]
    idp_url = values["NEON_IDP_URL"]
    monitoring_endpoint = values["NEON_MONITORING_ENDPOINT"]
    _reject_local_database(database_url)
    _require_database_tls(database_url)
    _require_https("NEON_IDP_URL", idp_url)
    _require_https("NEON_MONITORING_ENDPOINT", monitoring_endpoint)
    _validate_database_user(database_user)

    client_id = values["NEON_IDP_CLIENT_ID"]
    if not client_id.strip() or client_id != client_id.strip() or any(ord(c) < 32 for c in client_id):
        raise RuntimeError("NEON_IDP_CLIENT_ID must be non-empty and must not have surrounding whitespace or control characters")

    secrets = {name: secret_provider.get_required(name) for name in _REQUIRED_SECRETS}
    return ProductionConfig(
        database_url=database_url,
        database_user=database_user,
        database_password=secrets["NEON_DB_PASSWORD"],
        idp_url=idp_url,
        idp_client_id=client_id,
        idp_client_secret=secrets["NEON_IDP_CLIENT_SECRET"],
        database_pepper=secrets["NEON_DB_PEPPER"],
        monitoring_endpoint=monitoring_endpoint,
    )
