"""Local backend entry point; public deployment must use a managed production adapter."""
from __future__ import annotations

import os

from backend.composition import build_service
from backend.http_api import serve
from backend.store import AuthStore


if __name__ == "__main__":
    if os.environ.get("NEON_AUTH_ENV") == "production":
        # Production must inject a managed durable adapter through its composition root.
        # The local executable intentionally has no production database fallback.
        service = build_service()
        serve(service, os.environ.get("NEON_AUTH_HOST", "127.0.0.1"), int(os.environ.get("NEON_AUTH_PORT", "8080")))
    else:
        store = AuthStore(os.environ.get("NEON_AUTH_DB", "neon_shield_auth.sqlite3"))
        try:
            service = build_service()
            serve(service, os.environ.get("NEON_AUTH_HOST", "127.0.0.1"), int(os.environ.get("NEON_AUTH_PORT", "8080")))
        finally:
            store.close()
