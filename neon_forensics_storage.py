"""Safe orchestration helpers for storing approved Neon Forensics evidence."""
from __future__ import annotations

from pathlib import Path

from neon_forensics import CollectionClass, Incident, EvidenceItem, add_evidence
from neon_forensics_vault import EvidenceVault


def store_evidence(vault: EvidenceVault, incident: Incident, content: bytes, *,
                   source: str, content_type: str, classification: CollectionClass,
                   metadata: dict | None = None, consent_granted: bool = False) -> EvidenceItem:
    """Validate evidence through the policy engine, then encrypt it locally."""
    item = add_evidence(
        incident,
        content,
        source=source,
        content_type=content_type,
        classification=classification,
        metadata=metadata,
        consent_granted=consent_granted,
    )
    vault.put(
        item.evidence_id,
        content,
        collected_at_utc=item.collected_at_utc,
        classification=item.classification.value,
        content_type=item.content_type,
    )
    return item


def purge_expired(vault: EvidenceVault) -> list[str]:
    """Run the configured retention policy."""
    return vault.purge_expired()
