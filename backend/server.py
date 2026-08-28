"""Local backend entry point; public deployment must terminate TLS upstream."""
from __future__ import annotations

import os

from backend.http_api import serve
from backend.service import PersistentIdentityService
from backend.store import AuthStore


if __name__ == "__main__":
    store = AuthStore(os.environ.get("NEON_AUTH_DB", "neon_shield_auth.sqlite3"))
    try:
        service = PersistentIdentityService(store)
        serve(service, os.environ.get("NEON_AUTH_HOST", "127.0.0.1"), int(os.environ.get("NEON_AUTH_PORT", "8080")))
    finally:
        store.close()
