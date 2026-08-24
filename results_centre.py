"""Read-only results centre for Neon Shield investigations."""
from __future__ import annotations

from dataclasses import dataclass
from evidence_vault import EvidenceVault


@dataclass(frozen=True)
class InvestigationSummary:
    investigation_id: str
    evidence_count: int
    pending_review_count: int
    highest_confidence: float
    digest: str


def summarise_investigations(vault: EvidenceVault) -> list[InvestigationSummary]:
    """Return deterministic summaries for every investigation in the vault."""
    records = vault.records()
    grouped: dict[str, list] = {}
    for record in records:
        grouped.setdefault(record.investigation_id, []).append(record)

    summaries = []
    for investigation_id, items in grouped.items():
        summaries.append(
            InvestigationSummary(
                investigation_id=investigation_id,
                evidence_count=len(items),
                pending_review_count=sum(item.review_status == "PENDING_REVIEW" for item in items),
                highest_confidence=max(item.confidence for item in items),
                digest=vault.digest(investigation_id),
            )
        )
    return sorted(summaries, key=lambda item: item.investigation_id.casefold())


def search_investigations(vault: EvidenceVault, query: str) -> list[InvestigationSummary]:
    """Search investigation IDs, source paths, and candidate paths read-only."""
    needle = query.casefold().strip()
    if not needle:
        return summarise_investigations(vault)

    matching_ids = {
        record.investigation_id
        for record in vault.records()
        if needle in record.investigation_id.casefold()
        or needle in record.source.casefold()
        or needle in record.candidate.casefold()
    }
    return [item for item in summarise_investigations(vault) if item.investigation_id in matching_ids]
