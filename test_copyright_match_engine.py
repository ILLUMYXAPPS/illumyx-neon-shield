from copyright_match_engine import MatchEvidence, assess_match, rank_matches, transcript_block


def test_scores_weighted_signals_and_level():
    result = assess_match(MatchEvidence(audio=100, lyrics=100, artwork=100, metadata=100))
    assert result.score == 100.0
    assert result.level == "CRITICAL"


def test_values_are_clamped():
    result = assess_match(MatchEvidence(audio=140, lyrics=-10))
    assert result.score == 50.0
    assert result.level == "MEDIUM"


def test_rank_is_strongest_first():
    ranked = rank_matches([
        ("weak", MatchEvidence(audio=20)),
        ("strong", MatchEvidence(audio=90)),
    ])
    assert [name for name, _ in ranked] == ["strong", "weak"]


def test_transcript_marks_candidate_for_verification():
    text = transcript_block("track-copy.mp3", assess_match(MatchEvidence(audio=80, lyrics=60)))
    assert "track-copy.mp3" in text
    assert "VERIFY BEFORE MAKING ANY COPYRIGHT CLAIM" in text
