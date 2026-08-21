import unittest

from protection_profiles import ProtectionType, get_profile, list_profiles


class ProtectionProfileTests(unittest.TestCase):
    def test_all_profiles_have_stable_identity(self):
        profiles = list_profiles()
        self.assertEqual([p.key for p in profiles], [
            "music_audio", "documents", "images", "video", "projects", "custom"
        ])
        self.assertEqual(len({p.key for p in profiles}), len(profiles))

    def test_profiles_select_relevant_evidence(self):
        self.assertIn("transcript", get_profile("music_audio").evidence)
        self.assertIn("visual", get_profile("images").evidence)
        self.assertIn("structure", get_profile("projects").evidence)
        self.assertIn(ProtectionType.CUSTOM, get_profile("custom").types)

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            get_profile("not-a-profile")


if __name__ == "__main__":
    unittest.main()
