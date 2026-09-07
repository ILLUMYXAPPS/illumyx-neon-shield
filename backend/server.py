"""Local backend entry point; public deployment must terminate TLS upstream."""
from __future__ import annotations

import os

from backend.http_api import serve
from backend.service import PersistentIdentityService
from backend.store import AuthStore


_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _require_local_runtime() -> None:
    """Prevent the reference SQLite/HTTP server from being exposed as production."""
    environment = os.environ.get("NEON_AUTH_ENV", "development").strip().lower()
    host = os.environ.get("NEON_AUTH_HOST", "127.0.0.1").strip()

    if environment == "production":
        raise RuntimeError(
            "Production deployment is disabled for the local reference server. "
            "Use a managed production adapter with TLS, durable persistence, "
            "secret management, and monitoring."
        )
    if host not in _LOCAL_HOSTS:
        raise RuntimeError(
            "Local reference server may bind only to loopback. "
            "Terminate TLS in a managed reverse proxy for public deployment."
        )


if __name__ == "__main__":
    _require_local_runtime()
    store = AuthStore(os.environ.get("NEON_AUTH_DB", "neon_shield_auth.sqlite3"))
    try:
        service = PersistentIdentityService(store)
        serve(
            service,
            os.environ.get("NEON_AUTH_HOST", "127.0.0.1"),
            int(os.environ.get("NEON_AUTH_PORT", "8080")),
        )
    finally:
        store.close()
