from copyright_match_engine import MatchEvidence, assess_match, transcript_block


def test_transcript_contains_stable_review_fields():
    assessment = assess_match(MatchEvidence(audio=100, artwork=80))
    block = transcript_block("candidate.mp3", assessment)

    assert "CANDIDATE: candidate.mp3" in block
    assert "CONFIDENCE: 62.0%" in block
    assert "LEVEL: MEDIUM" in block
    assert "STATUS: CANDIDATE MATCH - VERIFY BEFORE MAKING ANY COPYRIGHT CLAIM" in block


def test_transcript_is_deterministic_for_same_evidence():
    evidence = MatchEvidence(audio=75, lyrics=50, artwork=25, metadata=10)
    assessment = assess_match(evidence)
    assert transcript_block("candidate.mp3", assessment) == transcript_block("candidate.mp3", assessment)


def test_empty_evidence_is_explicitly_non_match():
    block = transcript_block("candidate.mp3", assess_match(MatchEvidence()))
    assert "CONFIDENCE: 0.0%" in block
    assert "LEVEL: LOW" in block
    assert "No positive evidence signals." in block
    assert "CANDIDATE MATCH" in block
