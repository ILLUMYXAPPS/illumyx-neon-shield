import unittest

from review_engine import MatchReview, ReviewStatus


class MatchReviewTests(unittest.TestCase):
    def test_confirmed_match_records_audit(self):
        review = MatchReview("candidate-1")
        entry = review.decide(ReviewStatus.CONFIRMED_MATCH, "Evidence verified")
        self.assertEqual(review.status, ReviewStatus.CONFIRMED_MATCH)
        self.assertEqual(entry.previous_status, ReviewStatus.NEEDS_REVIEW)
        self.assertEqual(entry.new_status, ReviewStatus.CONFIRMED_MATCH)
        self.assertEqual(review.transcript()["audit"][0]["reason"], "Evidence verified")

    def test_decision_requires_reason(self):
        review = MatchReview("candidate-2")
        with self.assertRaises(ValueError):
            review.decide(ReviewStatus.FALSE_POSITIVE, " ")

    def test_cannot_decide_needs_review(self):
        review = MatchReview("candidate-3")
        with self.assertRaises(ValueError):
            review.decide(ReviewStatus.NEEDS_REVIEW, "Not a decision")

    def test_dismissed_status_supported(self):
        review = MatchReview("candidate-4")
        review.decide(ReviewStatus.DISMISSED, "Reviewed and dismissed")
        self.assertEqual(review.status, ReviewStatus.DISMISSED)


if __name__ == "__main__":
    unittest.main()
