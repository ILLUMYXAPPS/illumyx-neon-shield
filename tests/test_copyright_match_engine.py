from copyright_match_engine import MatchEvidence, assess_match, rank_matches, transcript_block


def test_assess_match_clamps_and_classifies():
    result = assess_match(MatchEvidence(audio=120, lyrics=-10, artwork=100, metadata=100))
    assert result.score == 65.0
    assert result.level == "MEDIUM"
    assert result.reasons == (
        "audio evidence 100.0%",
        "artwork evidence 100.0%",
        "metadata evidence 100.0%",
    )


def test_thresholds_are_stable():
    assert assess_match(MatchEvidence(audio=100, lyrics=100, artwork=100, metadata=100)).level == "CRITICAL"
    assert assess_match(MatchEvidence(audio=100, lyrics=100)).level == "HIGH"
    assert assess_match(MatchEvidence(audio=100)).level == "MEDIUM"
    assert assess_match(MatchEvidence(lyrics=100)).level == "MEDIUM"
    assert assess_match(MatchEvidence(metadata=49.9)).level == "LOW"


def test_equal_scores_rank_by_candidate_name():
    ranked = rank_matches([
        ("Zulu", MatchEvidence(audio=50)),
        ("Alpha", MatchEvidence(audio=50)),
        ("Bravo", MatchEvidence(audio=50)),
    ])
    assert [name for name, _ in ranked] == ["Alpha", "Bravo", "Zulu"]


def test_transcript_preserves_review_only_status():
    block = transcript_block("candidate.mp3", assess_match(MatchEvidence(audio=100)))
    assert "CANDIDATE: candidate.mp3" in block
    assert "STATUS: CANDIDATE MATCH - VERIFY BEFORE MAKING ANY COPYRIGHT CLAIM" in block
