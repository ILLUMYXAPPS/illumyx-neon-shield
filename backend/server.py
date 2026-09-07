"""Backend entry point; production cannot fall back to local persistence."""
from __future__ import annotations

import os

from backend.composition import build_service
from backend.http_api import serve


if __name__ == "__main__":
    service = build_service()
    try:
        serve(service, os.environ.get("NEON_AUTH_HOST", "127.0.0.1"), int(os.environ.get("NEON_AUTH_PORT", "8080")))
    finally:
        service.store.close()
