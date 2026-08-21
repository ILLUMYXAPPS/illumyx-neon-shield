"""Integration layer from copyright match candidates into review decisions."""

from dataclasses import dataclass
from typing import Mapping, Any

from review_engine import MatchReview, ReviewStatus


@dataclass(frozen=True)
class MatchCandidate:
    candidate_id: str
    score: float
    evidence: Mapping[str, Any]


def create_review(candidate: MatchCandidate) -> MatchReview:
    """Create a review item while preserving scanner evidence for audit context."""
    review = MatchReview(candidate.candidate_id)
    return review


def review_transcript(candidate: MatchCandidate, review: MatchReview) -> dict[str, object]:
    """Return a combined scanner evidence + review decision transcript."""
    transcript = review.transcript()
    transcript["score"] = candidate.score
    transcript["evidence"] = dict(candidate.evidence)
    return transcript


def decide_candidate(candidate: MatchCandidate, status: ReviewStatus, reason: str) -> dict[str, object]:
    """Apply a human review decision and return the auditable transcript."""
    review = create_review(candidate)
    review.decide(status, reason)
    return review_transcript(candidate, review)
