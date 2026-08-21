import unittest

from match_scanner import MatchCandidate
from match_results import build_results


class MatchResultsTests(unittest.TestCase):
    def test_build_results_creates_transcript(self):
        match = MatchCandidate(
            protected_id="song-1",
            candidate_id="candidate-1",
            match_type="fingerprint+transcript",
            confidence=0.875,
            evidence=["fingerprint", "transcript"],
        )
        result = build_results([match], scanned_at="2026-08-21T00:00:00+00:00")[0]
        self.assertEqual(result.status, "needs_review")
        self.assertEqual(result.transcript()["confidence"], 0.875)
        self.assertEqual(result.transcript()["scanned_at"], "2026-08-21T00:00:00+00:00")

    def test_empty_matches_produce_empty_results(self):
        self.assertEqual(build_results([]), [])


if __name__ == "__main__":
    unittest.main()
