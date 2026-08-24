from evidence_vault import EvidenceRecord, EvidenceVault, new_investigation_id


def make_record(investigation_id: str, candidate: str = "candidate.mp3") -> EvidenceRecord:
    return EvidenceRecord.create(
        investigation_id=investigation_id,
        source="reference.mp3",
        candidate=candidate,
        match_type="EXACT SHA-256",
        confidence=120,
        source_sha256="a" * 64,
        candidate_sha256="b" * 64,
        detail="Byte-for-byte identical file.",
    )


def test_record_clamps_confidence_and_defaults_to_review():
    record = make_record("INV-TEST")
    assert record.confidence == 100.0
    assert record.review_status == "PENDING_REVIEW"
    assert record.evidence_id
    assert record.recorded_at.endswith("+00:00")


def test_vault_is_append_only_and_filters_by_investigation(tmp_path):
    vault = EvidenceVault(tmp_path / "evidence.jsonl")
    first = make_record("INV-ONE", "a.mp3")
    second = make_record("INV-TWO", "b.mp3")
    vault.append(first)
    vault.append(second)

    assert vault.records("INV-ONE") == [first]
    assert vault.records("INV-TWO") == [second]
    assert vault.records() == [first, second]
    assert len((tmp_path / "evidence.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_investigation_digest_changes_when_evidence_changes(tmp_path):
    vault = EvidenceVault(tmp_path / "evidence.jsonl")
    investigation_id = new_investigation_id()
    vault.append(make_record(investigation_id, "a.mp3"))
    first_digest = vault.digest(investigation_id)
    vault.append(make_record(investigation_id, "b.mp3"))
    assert vault.digest(investigation_id) != first_digest
