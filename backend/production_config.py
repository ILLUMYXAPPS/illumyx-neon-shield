"""Fail-closed production configuration validation."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from backend.secrets import SecretProvider

_REQUIRED = ("NEON_AUTH_DB", "NEON_IDP_URL", "NEON_IDP_CLIENT_ID", "NEON_MONITORING_ENDPOINT")
_REQUIRED_SECRETS = ("NEON_IDP_CLIENT_SECRET", "NEON_DB_PEPPER")
_ALLOWED_DB_SSLMODES = {"require", "verify-ca", "verify-full"}


@dataclass(frozen=True)
class ProductionConfig:
    database_url: str
    idp_url: str
    idp_client_id: str
    idp_client_secret: str = field(repr=False)
    database_pepper: str = field(repr=False)
    monitoring_endpoint: str = ""


def _require_https(name: str, value: str) -> None:
    if not value or value != value.strip() or any(ord(char) < 32 for char in value):
        raise RuntimeError(f"{name} must be an absolute HTTPS URL without surrounding whitespace or control characters")
    try:
        parsed = urlparse(value)
        # Accessing hostname/port also forces urllib to reject malformed bracketed
        # hosts and invalid ports rather than accepting a superficially parsed URL.
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
    """Require explicit TLS for the PostgreSQL production connection."""
    try:
        parsed = urlparse(value)
        sslmodes = parse_qs(parsed.query).get("sslmode", [])
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise RuntimeError("NEON_AUTH_DB must be a valid PostgreSQL connection URL") from exc
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.netloc or not hostname:
        raise RuntimeError("NEON_AUTH_DB must use a valid PostgreSQL connection URL")
    if len(sslmodes) != 1 or sslmodes[0].lower() not in _ALLOWED_DB_SSLMODES:
        raise RuntimeError(
            "NEON_AUTH_DB must explicitly require TLS with sslmode=require, verify-ca, or verify-full"
        )


def validate_production_config(
    env: dict[str, str] | None = None,
    *,
    secret_provider: SecretProvider,
) -> ProductionConfig:
    """Validate production configuration and resolve secrets only via the provider."""
    values = os.environ if env is None else env
    if values.get("NEON_AUTH_ENV") != "production":
        raise RuntimeError("production configuration requires NEON_AUTH_ENV=production")
    missing = [name for name in _REQUIRED if not values.get(name)]
    if missing:
        raise RuntimeError("missing production configuration: " + ", ".join(missing))
    if secret_provider is None:
        raise RuntimeError("production configuration requires an injected SecretProvider")
    database_url = values["NEON_AUTH_DB"]
    idp_url = values["NEON_IDP_URL"]
    monitoring_endpoint = values["NEON_MONITORING_ENDPOINT"]
    _reject_local_database(database_url)
    _require_database_tls(database_url)
    _require_https("NEON_IDP_URL", idp_url)
    _require_https("NEON_MONITORING_ENDPOINT", monitoring_endpoint)
    client_id = values["NEON_IDP_CLIENT_ID"]
    if not client_id.strip() or client_id != client_id.strip():
        raise RuntimeError("NEON_IDP_CLIENT_ID must be non-empty and must not have surrounding whitespace")
    secrets = {name: secret_provider.get_required(name) for name in _REQUIRED_SECRETS}
    return ProductionConfig(
        database_url,
        idp_url,
        client_id,
        secrets["NEON_IDP_CLIENT_SECRET"],
        secrets["NEON_DB_PEPPER"],
        monitoring_endpoint,
    )
