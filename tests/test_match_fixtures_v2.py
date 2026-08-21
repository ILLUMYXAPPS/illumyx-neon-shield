import json
from pathlib import Path
import unittest

from match_review_pipeline import MatchCandidate, decide_candidate
from review_engine import ReviewStatus

FIXTURES = Path(__file__).parent / "fixtures" / "match_candidates.json"


class MatchFixtureCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads(FIXTURES.read_text())

    def test_fixture_transcripts_preserve_score_and_evidence(self):
        for name, data in self.fixtures.items():
            candidate = MatchCandidate(data["candidate_id"], data["score"], data["evidence"])
            status = ReviewStatus.CONFIRMED_MATCH if name in {"exact_match", "strong_partial_match"} else ReviewStatus.FALSE_POSITIVE
            transcript = decide_candidate(candidate, status, f"Fixture: {name}")
            self.assertEqual(transcript["score"], data["score"])
            self.assertEqual(transcript["evidence"], data["evidence"])
            self.assertEqual(transcript["candidate_id"], data["candidate_id"])

    def test_fixture_set_is_complete(self):
        self.assertEqual(set(self.fixtures), {"exact_match", "strong_partial_match", "lyrics_only", "metadata_only", "false_positive"})


if __name__ == "__main__":
    unittest.main()
