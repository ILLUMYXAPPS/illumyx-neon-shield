"""Read-only investigation report generation for Neon Shield."""
from __future__ import annotations

from evidence_vault import EvidenceRecord, EvidenceVault


def render_investigation_report(vault: EvidenceVault, investigation_id: str) -> str:
    """Render a deterministic human-review report without mutating evidence."""
    records = vault.records(investigation_id)
    lines = [
        "NEON SHIELD INVESTIGATION REPORT",
        f"INVESTIGATION: {investigation_id}",
        f"EVIDENCE COUNT: {len(records)}",
        f"EVIDENCE DIGEST: {vault.digest(investigation_id)}",
        "STATUS: HUMAN REVIEW REQUIRED",
        "",
    ]

    for index, record in enumerate(records, start=1):
        lines.extend([
            f"EVIDENCE {index}",
            f"ID: {record.evidence_id}",
            f"RECORDED: {record.recorded_at}",
            f"SOURCE: {record.source}",
            f"CANDIDATE: {record.candidate}",
            f"MATCH TYPE: {record.match_type}",
            f"CONFIDENCE: {record.confidence:.1f}%",
            f"SOURCE SHA-256: {record.source_sha256}",
            f"CANDIDATE SHA-256: {record.candidate_sha256}",
            f"REVIEW STATUS: {record.review_status}",
            f"DETAIL: {record.detail}",
            "",
        ])

    lines.extend([
        "IMPORTANT: Candidate matches are evidence for human review and are not automatic findings of copyright infringement.",
    ])
    return "\n".join(lines)
