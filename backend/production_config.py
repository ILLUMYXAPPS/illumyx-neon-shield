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


def _nonblank(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{name} must be a non-empty value")
    if value != value.strip() and name != "NEON_AUTH_DB":
        raise RuntimeError(f"{name} must not contain surrounding whitespace")
    return value


def _require_https(name: str, value: str) -> None:
    _nonblank(name, value)
    if any(char.isspace() for char in value):
        raise RuntimeError(f"{name} must not contain whitespace")
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
        port = parsed.port  # Force validation of malformed/out-of-range ports.
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a valid absolute HTTPS URL") from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise RuntimeError(f"{name} must be an absolute HTTPS URL without credentials or fragments")


def _reject_local_database(value: str) -> None:
    lowered = value.strip().lower()
    if lowered.startswith(("sqlite:", "sqlite3:", "file:")) or lowered in {":memory:", "memory"}:
        raise RuntimeError("NEON_AUTH_DB must identify a managed durable production database")
    if any(char.isspace() for char in value):
        raise RuntimeError("NEON_AUTH_DB must not contain whitespace")


def _require_database_tls(value: str) -> None:
    """Require explicit TLS for the PostgreSQL production connection."""
    try:
        parsed = urlparse(value)
        sslmodes = parse_qs(parsed.query, strict_parsing=True).get("sslmode", [])
    except ValueError as exc:
        raise RuntimeError("NEON_AUTH_DB must be a valid PostgreSQL connection URL") from exc
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise RuntimeError("NEON_AUTH_DB must use a PostgreSQL connection URL with a hostname")
    if parsed.password is None or parsed.username is None:
        raise RuntimeError("NEON_AUTH_DB must include managed-database credentials")
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
    missing = [name for name in _REQUIRED if not isinstance(values.get(name), str) or not values[name].strip()]
    if missing:
        raise RuntimeError("missing production configuration: " + ", ".join(missing))
    if secret_provider is None:
        raise RuntimeError("production configuration requires an injected SecretProvider")
    database_url = _nonblank("NEON_AUTH_DB", values["NEON_AUTH_DB"])
    idp_url = _nonblank("NEON_IDP_URL", values["NEON_IDP_URL"])
    client_id = _nonblank("NEON_IDP_CLIENT_ID", values["NEON_IDP_CLIENT_ID"])
    monitoring_endpoint = _nonblank("NEON_MONITORING_ENDPOINT", values["NEON_MONITORING_ENDPOINT"])
    _reject_local_database(database_url)
    _require_database_tls(database_url)
    _require_https("NEON_IDP_URL", idp_url)
    _require_https("NEON_MONITORING_ENDPOINT", monitoring_endpoint)
    secrets = {name: secret_provider.get_required(name) for name in _REQUIRED_SECRETS}
    for name, value in secrets.items():
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"missing required deployment secret: {name}")
    return ProductionConfig(
        database_url,
        idp_url,
        client_id,
        secrets["NEON_IDP_CLIENT_SECRET"],
        secrets["NEON_DB_PEPPER"],
        monitoring_endpoint,
    )
