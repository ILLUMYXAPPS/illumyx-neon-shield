from pathlib import Path

from copyright_scanner import fingerprint_reference, render_transcript, scan_targets


def test_exact_match_and_transcript(tmp_path: Path):
    refs = tmp_path / "refs"
    targets = tmp_path / "targets"
    refs.mkdir()
    targets.mkdir()
    source = refs / "ILLUMYX Track.wav"
    candidate = targets / "renamed-copy.wav"
    payload = b"ILLUMYX audio evidence" * 1000
    source.write_bytes(payload)
    candidate.write_bytes(payload)

    fingerprints = fingerprint_reference(refs)
    matches = scan_targets(fingerprints, targets)

    assert len(fingerprints) == 1
    assert len(matches) == 1
    assert matches[0].match_type == "EXACT SHA-256"
    assert matches[0].confidence == 100.0
    transcript = render_transcript(matches, len(fingerprints), targets)
    assert "MATCH #1" in transcript
    assert "VERIFY BEFORE MAKING ANY COPYRIGHT CLAIM" in transcript


def test_no_match(tmp_path: Path):
    refs = tmp_path / "refs"
    targets = tmp_path / "targets"
    refs.mkdir()
    targets.mkdir()
    (refs / "track.txt").write_text("one", encoding="utf-8")
    (targets / "different.txt").write_text("two", encoding="utf-8")

    fingerprints = fingerprint_reference(refs)
    matches = scan_targets(fingerprints, targets)

    assert matches == []
    assert "NO MATCHES DETECTED" in render_transcript(matches, len(fingerprints), targets)
