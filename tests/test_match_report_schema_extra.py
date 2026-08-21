import unittest
from pathlib import Path


class MatchReportSchemaExtraTests(unittest.TestCase):
    def test_transcript_schema_is_auditable(self):
        text = Path("MATCH_REPORT_SCHEMA.md").read_text()
        required = ["`candidate_id`", "`score`", "`evidence`", "`status`", "`audit`"]
        for item in required:
            self.assertIn(item, text)
        self.assertIn("Candidate -> Score -> Evidence -> Review -> Decision -> Audit", text)


if __name__ == "__main__":
    unittest.main()
