"""Local, profile-aware file match scanning primitives.

The scanner compares caller-supplied file fingerprints and metadata. It does
not crawl remote systems, make legal determinations, or submit claims.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List

from protection_profiles import ProtectionProfile, get_profile


@dataclass(frozen=True)
class MatchCandidate:
    protected_id: str
    candidate_id: str
    match_type: str
    confidence: float
    evidence: List[str]
    status: str = "needs_review"

    def transcript(self) -> Dict[str, object]:
        result = asdict(self)
        result["confidence"] = round(self.confidence, 4)
        return result


def _confidence(protected: Dict[str, object], candidate: Dict[str, object], profile: ProtectionProfile) -> tuple[float, List[str], str]:
    evidence: List[str] = []

    if protected.get("fingerprint") and protected.get("fingerprint") == candidate.get("fingerprint"):
        evidence.append("fingerprint")
    if protected.get("metadata") and protected.get("metadata") == candidate.get("metadata"):
        evidence.append("metadata")
    if "transcript" in profile.evidence and protected.get("transcript") and protected.get("transcript") == candidate.get("transcript"):
        evidence.append("transcript")
    if "text" in profile.evidence and protected.get("text") and protected.get("text") == candidate.get("text"):
        evidence.append("text")
    if "visual" in profile.evidence and protected.get("visual_hash") and protected.get("visual_hash") == candidate.get("visual_hash"):
        evidence.append("visual")
    if "structure" in profile.evidence and protected.get("structure") and protected.get("structure") == candidate.get("structure"):
        evidence.append("structure")

    if not evidence:
        return 0.0, [], "no_match"

    # Score against the profile evidence that is actually available on both
    # sides. Missing optional evidence must not penalise an otherwise valid
    # single-signal match.
    comparable_fields = []
    for field in profile.evidence:
        if field == "fingerprint":
            available = bool(protected.get("fingerprint") and candidate.get("fingerprint"))
        elif field == "metadata":
            available = bool(protected.get("metadata") and candidate.get("metadata"))
        elif field == "transcript":
            available = bool(protected.get("transcript") and candidate.get("transcript"))
        elif field == "text":
            available = bool(protected.get("text") and candidate.get("text"))
        elif field == "visual":
            available = bool(protected.get("visual_hash") and candidate.get("visual_hash"))
        elif field == "structure":
            available = bool(protected.get("structure") and candidate.get("structure"))
        elif field == "audio":
            available = bool(protected.get("audio_fingerprint") and candidate.get("audio_fingerprint"))
        else:
            available = False
        if available:
            comparable_fields.append(field)

    confidence = min(1.0, len(evidence) / max(1, len(comparable_fields)))
    match_type = "+".join(evidence)
    return confidence, evidence, match_type


def scan(protected: Dict[str, object], candidates: Iterable[Dict[str, object]], profile_key: str, threshold: float = 0.5) -> List[MatchCandidate]:
    """Compare a protected item against supplied candidates.

    Only candidates meeting the caller's confidence threshold are returned.
    Inputs are local/supplied data; discovery of external sources is outside
    this primitive.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    profile = get_profile(profile_key)
    protected_id = str(protected.get("id", "protected"))
    results: List[MatchCandidate] = []
    for candidate in candidates:
        confidence, evidence, match_type = _confidence(protected, candidate, profile)
        if confidence >= threshold:
            results.append(MatchCandidate(
                protected_id=protected_id,
                candidate_id=str(candidate.get("id", "candidate")),
                match_type=match_type,
                confidence=confidence,
                evidence=evidence,
            ))
    return results
