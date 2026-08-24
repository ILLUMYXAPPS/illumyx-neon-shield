"""Deterministic copyright candidate scoring for Neon Shield.

This module combines independent evidence signals into a review score. It does
not make legal infringement determinations or contact third parties.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MatchEvidence:
    audio: float = 0.0
    lyrics: float = 0.0
    artwork: float = 0.0
    metadata: float = 0.0


@dataclass(frozen=True)
class MatchAssessment:
    score: float
    level: str
    reasons: tuple[str, ...]


_WEIGHTS = {"audio": 0.50, "lyrics": 0.25, "artwork": 0.15, "metadata": 0.10}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def assess_match(evidence: MatchEvidence) -> MatchAssessment:
    values = {
        "audio": _clamp(evidence.audio),
        "lyrics": _clamp(evidence.lyrics),
        "artwork": _clamp(evidence.artwork),
        "metadata": _clamp(evidence.metadata),
    }
    score = round(sum(values[key] * weight for key, weight in _WEIGHTS.items()), 1)

    if score >= 90:
        level = "CRITICAL"
    elif score >= 75:
        level = "HIGH"
    elif score >= 50:
        level = "MEDIUM"
    else:
        level = "LOW"

    reasons = tuple(
        f"{key} evidence {values[key]:.1f}%"
        for key in _WEIGHTS
        if values[key] > 0
    )
    return MatchAssessment(score, level, reasons)


def rank_matches(items: Iterable[tuple[str, MatchEvidence]]) -> list[tuple[str, MatchAssessment]]:
    """Assess and sort candidates from strongest to weakest.

    Candidate names provide a deterministic tie-breaker so equal-scoring
    matches always appear in the same order in reports and evidence records.
    """
    ranked = [(name, assess_match(evidence)) for name, evidence in items]
    return sorted(ranked, key=lambda item: (-item[1].score, item[0].casefold(), item[0]))


def transcript_block(candidate: str, assessment: MatchAssessment) -> str:
    """Render a concise evidence block suitable for an existing transcript."""
    reasons = "; ".join(assessment.reasons) if assessment.reasons else "No positive evidence signals."
    return (
        f"CANDIDATE: {candidate}\n"
        f"CONFIDENCE: {assessment.score:.1f}%\n"
        f"LEVEL: {assessment.level}\n"
        f"SIGNALS: {reasons}\n"
        "STATUS: CANDIDATE MATCH - VERIFY BEFORE MAKING ANY COPYRIGHT CLAIM\n"
    )
