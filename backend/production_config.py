"""Deployment-neutral production configuration validation."""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

_REQUIRED = (
    "NEON_AUTH_DB",
    "NEON_IDP_URL",
    "NEON_IDP_CLIENT_ID",
    "NEON_IDP_CLIENT_SECRET",
    "NEON_SESSION_SECRET",
    "NEON_MONITORING_ENDPOINT",
)


@dataclass(frozen=True)
class ProductionConfig:
    database_url: str
    idp_url: str
    idp_client_id: str
    idp_client_secret: str
    session_secret: str
    monitoring_endpoint: str


def _require_https(name: str, value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"Production configuration requires HTTPS for {name}")


def _reject_local_database(value: str) -> None:
    scheme = urlparse(value).scheme.lower()
    if scheme in {"sqlite", "sqlite3", "file"} or value.startswith(":memory:"):
        raise RuntimeError("Production configuration requires a managed durable database; local SQLite is not allowed")


def validate_production_config(environ: dict[str, str] | None = None) -> ProductionConfig:
    """Read production configuration only from runtime environment and fail closed."""
    env = os.environ if environ is None else environ
    if env.get("NEON_AUTH_ENV") != "production":
        raise RuntimeError("Production configuration requires NEON_AUTH_ENV=production")
    missing = [name for name in _REQUIRED if not env.get(name, "").strip()]
    if missing:
        raise RuntimeError("Production configuration is incomplete; missing: " + ", ".join(missing))

    database_url = env["NEON_AUTH_DB"].strip()
    idp_url = env["NEON_IDP_URL"].strip()
    monitoring_endpoint = env["NEON_MONITORING_ENDPOINT"].strip()
    _reject_local_database(database_url)
    _require_https("NEON_IDP_URL", idp_url)
    _require_https("NEON_MONITORING_ENDPOINT", monitoring_endpoint)

    return ProductionConfig(
        database_url=database_url,
        idp_url=idp_url,
        idp_client_id=env["NEON_IDP_CLIENT_ID"].strip(),
        idp_client_secret=env["NEON_IDP_CLIENT_SECRET"].strip(),
        session_secret=env["NEON_SESSION_SECRET"].strip(),
        monitoring_endpoint=monitoring_endpoint,
    )
