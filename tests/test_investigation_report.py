from evidence_vault import EvidenceRecord, EvidenceVault
from investigation_report import render_investigation_report


def test_report_is_deterministic_and_read_only(tmp_path):
    path = tmp_path / "evidence.jsonl"
    vault = EvidenceVault(path)
    record = EvidenceRecord.create(
        investigation_id="INV-REPORT",
        source="reference.mp3",
        candidate="candidate.mp3",
        match_type="SAMPLED FINGERPRINT",
        confidence=82.5,
        source_sha256="a" * 64,
        candidate_sha256="b" * 64,
        detail="Candidate match requires verification.",
    )
    vault.append(record)
    before = path.read_text(encoding="utf-8")

    first = render_investigation_report(vault, "INV-REPORT")
    second = render_investigation_report(vault, "INV-REPORT")

    assert first == second
    assert "INVESTIGATION: INV-REPORT" in first
    assert "EVIDENCE COUNT: 1" in first
    assert "CONFIDENCE: 82.5%" in first
    assert "HUMAN REVIEW REQUIRED" in first
    assert "not automatic findings of copyright infringement" in first
    assert path.read_text(encoding="utf-8") == before


def test_empty_report_is_still_explicit_about_review(tmp_path):
    report = render_investigation_report(EvidenceVault(tmp_path / "empty.jsonl"), "INV-EMPTY")
    assert "EVIDENCE COUNT: 0" in report
    assert "HUMAN REVIEW REQUIRED" in report
