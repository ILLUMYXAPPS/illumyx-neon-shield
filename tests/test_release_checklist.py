import unittest
from pathlib import Path


class ReleaseChecklistTests(unittest.TestCase):
    def test_checklist_contains_release_gates(self):
        text = Path("RELEASE_CHECKLIST.md").read_text()
        for phrase in ("CI workflow", "Python 3.10 and 3.12", "macOS, Ubuntu, and Windows", "False-positive fixture", "Final smoke test", "Prerelease package/version"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
