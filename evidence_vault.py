"""Local-first evidence vault for Neon Shield copyright investigations.

Evidence records are append-only in the application model: callers create a
new record for each observation instead of mutating an earlier finding. The
vault stores references and hashes, not copied source-file contents.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable
from uuid import uuid4


@dataclass(frozen=True)
class EvidenceRecord:
    investigation_id: str
    evidence_id: str
    recorded_at: str
    source: str
    candidate: str
    match_type: str
    confidence: float
    source_sha256: str
    candidate_sha256: str
    detail: str
    review_status: str = "PENDING_REVIEW"

    @classmethod
    def create(
        cls,
        *,
        investigation_id: str,
        source: str,
        candidate: str,
        match_type: str,
        confidence: float,
        source_sha256: str,
        candidate_sha256: str,
        detail: str,
    ) -> "EvidenceRecord":
        confidence = max(0.0, min(100.0, float(confidence)))
        return cls(
            investigation_id=investigation_id,
            evidence_id=uuid4().hex,
            recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            source=source,
            candidate=candidate,
            match_type=match_type,
            confidence=confidence,
            source_sha256=source_sha256,
            candidate_sha256=candidate_sha256,
            detail=detail,
        )


class EvidenceVault:
    """JSONL-backed local evidence store.

    Each call to append writes one complete record. Existing records are never
    rewritten by the vault, making the on-disk history easy to audit.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def append(self, record: EvidenceRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

    def records(self, investigation_id: str | None = None) -> list[EvidenceRecord]:
        if not self.path.exists():
            return []
        result: list[EvidenceRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                data = json.loads(line)
                if investigation_id is None or data["investigation_id"] == investigation_id:
                    result.append(EvidenceRecord(**data))
        return sorted(result, key=lambda item: (item.recorded_at, item.evidence_id))

    def digest(self, investigation_id: str) -> str:
        """Return a reproducible digest of the investigation's evidence records."""
        payload = [asdict(item) for item in self.records(investigation_id)]
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def new_investigation_id() -> str:
    return f"INV-{uuid4().hex[:12].upper()}"
