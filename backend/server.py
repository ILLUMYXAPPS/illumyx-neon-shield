"""Backend entry point; production cannot fall back to local persistence."""
from __future__ import annotations

import os

from backend.composition import build_service
from backend.http_api import serve
from security.incident_evidence import EvidenceStore


if __name__ == "__main__":
    service = build_service()
    evidence_path = os.environ.get("NEON_EVIDENCE_DB")
    evidence_store = EvidenceStore(evidence_path) if evidence_path else None
    trusted_proxies = tuple(
        item.strip()
        for item in os.environ.get("NEON_TRUSTED_PROXY_CIDRS", "").split(",")
        if item.strip()
    )
    try:
        serve(
            service,
            os.environ.get("NEON_AUTH_HOST", "127.0.0.1"),
            int(os.environ.get("NEON_AUTH_PORT", "8080")),
            evidence_store=evidence_store,
            trusted_proxies=trusted_proxies,
        )
    finally:
        service.store.close()
