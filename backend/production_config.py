"""Deployment-neutral production configuration validation."""
from __future__ import annotations

import os
from dataclasses import dataclass

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

def validate_production_config(environ: dict[str, str] | None = None) -> ProductionConfig:
    """Read production configuration only from runtime environment and fail closed."""
    env = os.environ if environ is None else environ
    if env.get("NEON_AUTH_ENV") != "production":
        raise RuntimeError("Production configuration requires NEON_AUTH_ENV=production")
    missing = [name for name in _REQUIRED if not env.get(name, "").strip()]
    if missing:
        raise RuntimeError("Production configuration is incomplete; missing: " + ", ".join(missing))
    return ProductionConfig(
        database_url=env["NEON_AUTH_DB"].strip(),
        idp_url=env["NEON_IDP_URL"].strip(),
        idp_client_id=env["NEON_IDP_CLIENT_ID"].strip(),
        idp_client_secret=env["NEON_IDP_CLIENT_SECRET"].strip(),
        session_secret=env["NEON_SESSION_SECRET"].strip(),
        monitoring_endpoint=env["NEON_MONITORING_ENDPOINT"].strip(),
    )
