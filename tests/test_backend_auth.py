import unittest

from backend.auth_service import AuthError, AuthStore


class BackendAuthTests(unittest.TestCase):
    def setUp(self):
        self.store = AuthStore()
        self.user_id = self.store.create_user("owner@example.test", "correct horse battery staple")
        self.device = "device-001"
        self.store.enroll_device(self.user_id, self.device)

    def tearDown(self):
        self.store.close()

    def test_trusted_device_receives_server_session(self):
        session = self.store.authenticate("owner@example.test", "correct horse battery staple", self.device)
        validated = self.store.validate_session(session.token)
        self.assertEqual(validated.user_id, self.user_id)
        self.assertEqual(validated.device_id, self.device)

    def test_unrecognised_device_is_denied(self):
        with self.assertRaisesRegex(AuthError, "device is not trusted"):
            self.store.authenticate("owner@example.test", "correct horse battery staple", "device-999")

    def test_revoked_device_cannot_use_existing_session(self):
        session = self.store.authenticate("owner@example.test", "correct horse battery staple", self.device)
        self.store.revoke_device(self.user_id, self.device)
        with self.assertRaisesRegex(AuthError, "session denied"):
            self.store.validate_session(session.token)

    def test_blocked_identity_cannot_authenticate(self):
        self.store.set_blocked(self.user_id)
        with self.assertRaisesRegex(AuthError, "authentication denied"):
            self.store.authenticate("owner@example.test", "correct horse battery staple", self.device)

    def test_revoked_session_is_denied(self):
        session = self.store.authenticate("owner@example.test", "correct horse battery staple", self.device)
        self.store.revoke_session(session.token)
        with self.assertRaisesRegex(AuthError, "session denied"):
            self.store.validate_session(session.token)


if __name__ == "__main__":
    unittest.main()
