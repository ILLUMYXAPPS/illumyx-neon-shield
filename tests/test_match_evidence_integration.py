from copyright_match_engine import MatchEvidence, record_match
from evidence_vault import EvidenceVault


def test_match_assessment_is_recorded_in_evidence_vault(tmp_path):
    vault = EvidenceVault(tmp_path / "evidence.jsonl")
    record = record_match(
        vault,
        investigation_id="INV-TEST123",
        source="reference.mp3",
        candidate="candidate.mp3",
        match_type="EXACT SHA-256",
        source_sha256="a" * 64,
        candidate_sha256="b" * 64,
        evidence=MatchEvidence(audio=100, artwork=50),
        detail="Fingerprint match candidate.",
    )

    assert record.investigation_id == "INV-TEST123"
    assert record.confidence == 57.5
    assert record.review_status == "PENDING_REVIEW"
    assert vault.records("INV-TEST123") == [record]
    assert "Level: MEDIUM" in record.detail
    assert "audio evidence 100.0%" in record.detail


def test_record_match_does_not_modify_source_files(tmp_path):
    vault = EvidenceVault(tmp_path / "evidence.jsonl")
    record_match(
        vault,
        investigation_id="INV-SAFE",
        source="/reference.mp3",
        candidate="/candidate.mp3",
        match_type="SAMPLED FINGERPRINT",
        source_sha256="a" * 64,
        candidate_sha256="b" * 64,
        evidence=MatchEvidence(audio=90),
        detail="Candidate requires review.",
    )
    assert not (tmp_path / "reference.mp3").exists()
    assert not (tmp_path / "candidate.mp3").exists()
