"""Fail-closed production configuration validation."""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.secrets import EnvironmentSecretProvider, SecretProvider

_REQUIRED = ("NEON_AUTH_DB", "NEON_IDP_URL", "NEON_IDP_CLIENT_ID", "NEON_MONITORING_ENDPOINT")


@dataclass(frozen=True)
class ProductionConfig:
    database_url: str
    idp_url: str
    idp_client_id: str
    idp_client_secret: str
    session_secret: str
    database_pepper: str
    monitoring_endpoint: str


def _require_https(name: str, value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"{name} must be an absolute HTTPS URL")


def _reject_local_database(value: str) -> None:
    lowered = value.lower()
    if lowered.startswith(("sqlite:", "sqlite3:", "file:")) or lowered in {":memory:", "memory"}:
        raise RuntimeError("NEON_AUTH_DB must identify a managed durable production database")


def validate_production_config(
    env: dict[str, str] | None = None,
    *,
    secret_provider: SecretProvider | None = None,
) -> ProductionConfig:
    values = os.environ if env is None else env
    if values.get("NEON_AUTH_ENV") != "production":
        raise RuntimeError("production configuration requires NEON_AUTH_ENV=production")
    missing = [name for name in _REQUIRED if not values.get(name)]
    if missing:
        raise RuntimeError("missing production configuration: " + ", ".join(missing))
    provider = secret_provider or EnvironmentSecretProvider(values)
    database_url = values["NEON_AUTH_DB"]
    idp_url = values["NEON_IDP_URL"]
    monitoring_endpoint = values["NEON_MONITORING_ENDPOINT"]
    _reject_local_database(database_url)
    _require_https("NEON_IDP_URL", idp_url)
    _require_https("NEON_MONITORING_ENDPOINT", monitoring_endpoint)
    return ProductionConfig(
        database_url,
        idp_url,
        values["NEON_IDP_CLIENT_ID"],
        provider.get_required("NEON_IDP_CLIENT_SECRET"),
        provider.get_required("NEON_SESSION_SECRET"),
        provider.get_required("NEON_DB_PEPPER"),
        monitoring_endpoint,
    )
