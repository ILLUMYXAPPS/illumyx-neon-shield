import json

from copyright_online_sweep import OnlineCopyrightSweep, SweepTarget


def test_search_queries_include_title_and_artist():
    target = SweepTarget("work-001", "Imperfection Is Perfection")
    queries = OnlineCopyrightSweep.search_queries(target)
    assert '"Imperfection Is Perfection"' in queries
    assert '"Imperfection Is Perfection" ILLUMYX' in queries


def test_record_and_export_candidate(tmp_path):
    sweep = OnlineCopyrightSweep(tmp_path / "evidence.jsonl")
    target = SweepTarget("work-001", "Imperfection Is Perfection")
    record = sweep.record_candidate(
        target,
        "https://example.com/upload",
        "example",
        "title_candidate",
        0.91,
    )
    assert record.confidence == 0.91
    exported = sweep.export_transcript(tmp_path / "transcript.json")
    payload = json.loads(exported.read_text(encoding="utf-8"))
    assert payload["status"] == "candidate_matches_require_verification"
    assert payload["matches"][0]["url"] == "https://example.com/upload"


def test_rejects_invalid_confidence(tmp_path):
    sweep = OnlineCopyrightSweep(tmp_path / "evidence.jsonl")
    target = SweepTarget("work-001", "Track")
    try:
        sweep.record_candidate(target, "https://example.com", "example", "match", 1.1)
    except ValueError as exc:
        assert "Confidence" in str(exc)
    else:
        raise AssertionError("Expected invalid confidence to be rejected")
