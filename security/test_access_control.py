import unittest

from .access_control import AccessControl, generate_owner_secret


class AccessControlTests(unittest.TestCase):
    def setUp(self):
        self.salt = b"test-only-salt"
        self.owner = generate_owner_secret()
        self.acl = AccessControl()
        self.acl.initialize_owner(self.owner, self.salt)

    def test_owner_can_add_and_remove_trusted_device(self):
        self.acl.add_trusted_device(self.owner, self.salt, "trusted-1")
        self.assertTrue(self.acl.is_trusted("trusted-1"))
        self.acl.remove_trusted_device(self.owner, self.salt, "trusted-1")
        self.assertFalse(self.acl.is_trusted("trusted-1"))

    def test_wrong_token_cannot_change_trusted_devices(self):
        with self.assertRaises(PermissionError):
            self.acl.add_trusted_device("wrong-token", self.salt, "attacker-device")
        self.assertFalse(self.acl.is_trusted("attacker-device"))

    def test_ownership_cannot_be_reinitialized(self):
        with self.assertRaises(PermissionError):
            self.acl.initialize_owner("replacement", self.salt)
        self.assertTrue(self.acl.verify_owner(self.owner, self.salt))

    def test_audit_records_failed_change(self):
        with self.assertRaises(PermissionError):
            self.acl.remove_trusted_device("wrong-token", self.salt, "trusted-1")
        self.assertEqual(self.acl.audit_log[-1].action, "trusted_device_remove")
        self.assertFalse(self.acl.audit_log[-1].success)


if __name__ == "__main__":
    unittest.main()
