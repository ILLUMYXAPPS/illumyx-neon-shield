import unittest
from pathlib import Path


class MatchReportSchemaTests(unittest.TestCase):
    def test_schema_documents_core_audit_fields_and_flow(self):
        text = Path("MATCH_REPORT_SCHEMA.md").read_text()
        for field in ("candidate_id", "score", "evidence", "status", "audit"):
            self.assertIn(f"`{field}`", text)
        self.assertIn("Candidate -> Score -> Evidence -> Review -> Decision -> Audit", text)


if __name__ == "__main__":
    unittest.main()
