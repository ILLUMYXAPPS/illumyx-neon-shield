import unittest

from match_review_pipeline import MatchCandidate, decide_candidate, review_transcript
from review_engine import MatchReview, ReviewStatus


class MatchReviewPipelineTests(unittest.TestCase):
    def test_candidate_evidence_flows_into_transcript(self):
        candidate = MatchCandidate("candidate-1", 0.92, {"audio": 0.95, "lyrics": 0.88})
        review = MatchReview(candidate.candidate_id)
        review.decide(ReviewStatus.CONFIRMED_MATCH, "Evidence verified")
        transcript = review_transcript(candidate, review)
        self.assertEqual(transcript["score"], 0.92)
        self.assertEqual(transcript["evidence"]["audio"], 0.95)
        self.assertEqual(transcript["status"], "confirmed_match")

    def test_decision_returns_auditable_result(self):
        candidate = MatchCandidate("candidate-2", 0.41, {"metadata": 0.6})
        result = decide_candidate(candidate, ReviewStatus.FALSE_POSITIVE, "Metadata-only overlap")
        self.assertEqual(result["candidate_id"], "candidate-2")
        self.assertEqual(result["status"], "false_positive")
        self.assertEqual(result["audit"][0]["reason"], "Metadata-only overlap")


if __name__ == "__main__":
    unittest.main()
