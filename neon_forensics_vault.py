"""Encrypted local evidence storage and retention for Neon Forensics.

The vault is local-first: evidence is encrypted before it is written to disk,
and nothing is uploaded by this module. The caller supplies a key obtained from
an OS-backed secret store or another approved key-management mechanism.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class RetentionPolicy:
    """Retention windows in days. Zero means purge immediately after export."""
    standard_days: int = 30
    forensic_days: int = 90
    user_submitted_days: int = 90
    minimum_free_space_mb: int = 512

    def __post_init__(self) -> None:
        if min(self.standard_days, self.forensic_days, self.user_submitted_days) < 0:
            raise ValueError("retention periods cannot be negative")
        if self.minimum_free_space_mb < 0:
            raise ValueError("minimum_free_space_mb cannot be negative")


class EvidenceVault:
    """AES-256-GCM encrypted evidence vault with explicit retention cleanup."""

    VERSION = 1
    NONCE_BYTES = 12

    def __init__(self, root: str | Path, key: bytes, policy: RetentionPolicy | None = None) -> None:
        if len(key) != 32:
            raise ValueError("EvidenceVault requires a 32-byte AES-256 key")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._aes = AESGCM(key)
        self.policy = policy or RetentionPolicy()

    def put(self, evidence_id: str, content: bytes, *, collected_at_utc: str,
            classification: str, content_type: str) -> Path:
        """Encrypt one evidence payload and return its local path."""
        safe_id = "".join(c for c in evidence_id if c.isalnum() or c in "-_")
        if not safe_id:
            raise ValueError("invalid evidence_id")
        nonce = os.urandom(self.NONCE_BYTES)
        aad = json.dumps({
            "version": self.VERSION,
            "evidence_id": safe_id,
            "classification": classification,
            "content_type": content_type,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ciphertext = self._aes.encrypt(nonce, content, aad)
        path = self.root / f"{safe_id}.nse"
        tmp = path.with_suffix(".tmp")
        envelope = {
            "version": self.VERSION,
            "evidence_id": safe_id,
            "collected_at_utc": collected_at_utc,
            "classification": classification,
            "content_type": content_type,
            "nonce": nonce.hex(),
            "aad": aad.decode("utf-8"),
            "ciphertext": ciphertext.hex(),
        }
        tmp.write_text(json.dumps(envelope, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)
        return path

    def get(self, evidence_id: str) -> bytes:
        path = self.root / f"{evidence_id}.nse"
        envelope = json.loads(path.read_text(encoding="utf-8"))
        aad = envelope["aad"].encode("utf-8")
        return self._aes.decrypt(bytes.fromhex(envelope["nonce"]), bytes.fromhex(envelope["ciphertext"]), aad)

    def purge_expired(self, *, now: datetime | None = None) -> list[str]:
        """Delete expired encrypted evidence according to its classification."""
        now = now or datetime.now(timezone.utc)
        deleted: list[str] = []
        for path in self.root.glob("*.nse"):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
                collected = datetime.fromisoformat(envelope["collected_at_utc"].replace("Z", "+00:00"))
                classification = envelope.get("classification", "SAFE_TO_COLLECT")
                if classification == "USER_SUBMITTED":
                    days = self.policy.user_submitted_days
                elif classification == "CONSENT_REQUIRED":
                    days = self.policy.forensic_days
                else:
                    days = self.policy.standard_days
                if collected + timedelta(days=days) <= now:
                    path.unlink(missing_ok=True)
                    deleted.append(path.name)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                # Corrupt/unreadable evidence is not silently deleted by retention.
                continue
        return deleted

    def purge_incident(self, incident_id: str) -> bool:
        """Remove all vault evidence whose filename starts with an incident prefix."""
        prefix = "".join(c for c in incident_id if c.isalnum() or c in "-_" )
        removed = False
        for path in self.root.glob(f"{prefix}*.nse"):
            path.unlink(missing_ok=True)
            removed = True
        return removed

    def available_space_mb(self) -> int:
        return shutil.disk_usage(self.root).free // (1024 * 1024)

    def should_pause_collection(self) -> bool:
        return self.available_space_mb() < self.policy.minimum_free_space_mb
