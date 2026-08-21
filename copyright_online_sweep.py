"""Online copyright sweep evidence pipeline.

This module deliberately separates discovery from infringement conclusions. It
creates deterministic public-search queries from the ILLUMYX fingerprint
registry and stores verified candidate URLs as timestamped evidence records.
No remote crawling or automated takedown action is performed here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus


@dataclass(frozen=True)
class SweepTarget:
    work_id: str
    title: str
    artist: str = "ILLUMYX"
    sha256: str | None = None
    identifiers: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateEvidence:
    work_id: str
    source_title: str
    url: str
    platform: str
    match_type: str
    confidence: float
    discovered_at: str
    evidence_note: str = "Candidate match requiring verification"


class OnlineCopyrightSweep:
    """Build search targets and persist candidate-match evidence."""

    def __init__(self, evidence_path: str | Path = "copyright_evidence.jsonl") -> None:
        self.evidence_path = Path(evidence_path)

    @staticmethod
    def search_queries(target: SweepTarget) -> list[str]:
        values = [target.title, f'"{target.title}" {target.artist}']
        values.extend(target.identifiers)
        return [f'"{value}"' if " " in value and not value.startswith('"') else value for value in values]

    @staticmethod
    def search_urls(target: SweepTarget) -> list[str]:
        return [f"https://www.google.com/search?q={quote_plus(query)}" for query in OnlineCopyrightSweep.search_queries(target)]

    def record_candidate(
        self,
        target: SweepTarget,
        url: str,
        platform: str,
        match_type: str,
        confidence: float,
        source_title: str | None = None,
        evidence_note: str = "Candidate match requiring verification",
    ) -> CandidateEvidence:
        if not url.startswith(("https://", "http://")):
            raise ValueError("Evidence URL must be an HTTP(S) URL")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        record = CandidateEvidence(
            work_id=target.work_id,
            source_title=source_title or target.title,
            url=url,
            platform=platform,
            match_type=match_type,
            confidence=confidence,
            discovered_at=datetime.now(timezone.utc).isoformat(),
            evidence_note=evidence_note,
        )
        self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        with self.evidence_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        return record

    def transcript(self) -> list[dict]:
        if not self.evidence_path.exists():
            return []
        records: list[dict] = []
        for line in self.evidence_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return records

    def export_transcript(self, output_path: str | Path) -> Path:
        output = Path(output_path)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "candidate_matches_require_verification",
            "matches": self.transcript(),
        }
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output

    def scan_targets(self, targets: Iterable[SweepTarget]) -> dict[str, list[str]]:
        return {target.work_id: self.search_urls(target) for target in targets}
