"""Presentation-ready match result and transcript helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from match_scanner import MatchCandidate


@dataclass(frozen=True)
class MatchResult:
    protected_id: str
    candidate_id: str
    confidence: float
    evidence: List[str]
    match_type: str
    status: str
    scanned_at: str

    @classmethod
    def from_candidate(cls, candidate: MatchCandidate, scanned_at: str | None = None) -> "MatchResult":
        return cls(
            protected_id=candidate.protected_id,
            candidate_id=candidate.candidate_id,
            confidence=candidate.confidence,
            evidence=list(candidate.evidence),
            match_type=candidate.match_type,
            status=candidate.status,
            scanned_at=scanned_at or datetime.now(timezone.utc).isoformat(),
        )

    def transcript(self) -> Dict[str, object]:
        return {
            "protected_id": self.protected_id,
            "candidate_id": self.candidate_id,
            "confidence": round(self.confidence, 4),
            "evidence": list(self.evidence),
            "match_type": self.match_type,
            "status": self.status,
            "scanned_at": self.scanned_at,
        }


def build_results(matches: Iterable[MatchCandidate], scanned_at: str | None = None) -> List[MatchResult]:
    """Convert scanner candidates into stable UI/transcript records."""
    return [MatchResult.from_candidate(match, scanned_at=scanned_at) for match in matches]
