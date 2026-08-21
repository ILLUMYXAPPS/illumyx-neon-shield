import unittest

from match_scanner import scan


class MatchScannerTests(unittest.TestCase):
    def test_audio_fingerprint_and_transcript_match(self):
        protected = {
            "id": "song-1",
            "fingerprint": "abc",
            "metadata": {"title": "Track"},
            "transcript": "hello world",
        }
        candidates = [{
            "id": "candidate-1",
            "fingerprint": "abc",
            "metadata": {"title": "Track"},
            "transcript": "hello world",
        }]
        results = scan(protected, candidates, "music_audio", threshold=0.5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "needs_review")
        self.assertIn("fingerprint", results[0].evidence)
        self.assertIn("transcript", results[0].evidence)

    def test_profile_specific_evidence_is_respected(self):
        protected = {"id": "doc-1", "fingerprint": "abc", "transcript": "same"}
        candidates = [{"id": "candidate-1", "fingerprint": "abc", "transcript": "same"}]
        results = scan(protected, candidates, "documents", threshold=0.5)
        self.assertEqual(results[0].evidence, ["fingerprint"])

    def test_non_match_is_not_returned(self):
        protected = {"id": "img-1", "fingerprint": "abc"}
        candidates = [{"id": "candidate-1", "fingerprint": "xyz"}]
        self.assertEqual(scan(protected, candidates, "images"), [])

    def test_invalid_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            scan({"id": "x"}, [], "custom", threshold=1.1)


if __name__ == "__main__":
    unittest.main()
