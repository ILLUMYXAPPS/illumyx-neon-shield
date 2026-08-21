import unittest

from protection_dashboard import create_dashboard


class ProtectionDashboardTests(unittest.TestCase):
    def test_dashboard_uses_selected_profile(self):
        dashboard = create_dashboard("music_audio")
        snapshot = dashboard.snapshot()
        self.assertEqual(snapshot["profile"]["key"], "music_audio")
        self.assertIn("transcript", snapshot["profile"]["evidence"])

    def test_dashboard_starts_with_safe_empty_state(self):
        dashboard = create_dashboard("documents")
        snapshot = dashboard.snapshot()
        self.assertEqual(snapshot["stats"]["protected_files"], 0)
        self.assertEqual(snapshot["stats"]["scans_run"], 0)
        self.assertEqual(snapshot["stats"]["candidates"], 0)
        self.assertEqual(snapshot["stats"]["high_priority"], 0)
        self.assertEqual(snapshot["recent_matches"], [])
        self.assertEqual(snapshot["alerts"], [])

    def test_unknown_profile_fails_early(self):
        with self.assertRaises(ValueError):
            create_dashboard("not-a-profile")


if __name__ == "__main__":
    unittest.main()
