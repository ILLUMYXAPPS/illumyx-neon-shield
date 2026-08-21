import unittest

from ad_bugsworth import BugsworthProfile


class BugsworthTests(unittest.TestCase):
    def test_starts_at_level_one(self):
        profile = BugsworthProfile()
        self.assertEqual(profile.level.level, 1)
        self.assertEqual(profile.level.title, "Bug Spotter")

    def test_level_progression(self):
        profile = BugsworthProfile().record_catch(50)
        self.assertEqual(profile.level.level, 4)
        self.assertEqual(profile.level.badge, "🎯")
        self.assertEqual(profile.progress["remaining"], 50)

    def test_master_level_has_no_next_level(self):
        profile = BugsworthProfile().record_catch(1000)
        self.assertEqual(profile.level.level, 8)
        self.assertIsNone(profile.progress["next"])

    def test_invalid_catch_count_rejected(self):
        with self.assertRaises(ValueError):
            BugsworthProfile().record_catch(0)

    def test_summary(self):
        summary = BugsworthProfile().record_catch(10).summary()
        self.assertEqual(summary["name"], "A.D. Bugsworth")
        self.assertEqual(summary["role"], "Chief Bug Detection Officer")
        self.assertEqual(summary["level"], 2)


if __name__ == "__main__":
    unittest.main()
