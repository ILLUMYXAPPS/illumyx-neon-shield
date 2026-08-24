from evidence_vault import EvidenceRecord, EvidenceVault
from results_centre import search_investigations, summarise_investigations


def add(vault, investigation_id, source, candidate, confidence, status="PENDING_REVIEW"):
    vault.append(
        EvidenceRecord.create(
            investigation_id=investigation_id,
            source=source,
            candidate=candidate,
            match_type="FINGERPRINT",
            confidence=confidence,
            source_sha256="a" * 64,
            candidate_sha256="b" * 64,
            detail="Candidate evidence.",
        )
    )


def test_results_centre_summarises_and_sorts_investigations(tmp_path):
    vault = EvidenceVault(tmp_path / "evidence.jsonl")
    add(vault, "INV-Z", "z.mp3", "candidate-z.mp3", 70)
    add(vault, "INV-A", "a.mp3", "candidate-a.mp3", 92)
    add(vault, "INV-A", "a.mp3", "candidate-b.mp3", 55)

    summaries = summarise_investigations(vault)
    assert [item.investigation_id for item in summaries] == ["INV-A", "INV-Z"]
    assert summaries[0].evidence_count == 2
    assert summaries[0].pending_review_count == 2
    assert summaries[0].highest_confidence == 92.0


def test_results_searches_source_and_candidate_without_mutation(tmp_path):
    path = tmp_path / "evidence.jsonl"
    vault = EvidenceVault(path)
    add(vault, "INV-MUSIC", "reference.mp3", "suspect-copy.mp3", 88)
    add(vault, "INV-OTHER", "photo.png", "other.png", 60)
    before = path.read_text(encoding="utf-8")

    assert [item.investigation_id for item in search_investigations(vault, "suspect-copy")] == ["INV-MUSIC"]
    assert [item.investigation_id for item in search_investigations(vault, "reference")] == ["INV-MUSIC"]
    assert path.read_text(encoding="utf-8") == before
