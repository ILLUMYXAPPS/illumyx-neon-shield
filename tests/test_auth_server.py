import unittest
from datetime import timedelta

from auth_server import AuthenticationError, InMemoryIdentityService
from auth_server_contract import AuthFailure, SignInRequest


class AuthServerTests(unittest.TestCase):
    def setUp(self):
        self.service = InMemoryIdentityService(
            verify_credential=lambda identity, credential: (
                "subject-123"
                if identity == "user@example.test" and credential == "correct"
                else None
            ),
            trusted_devices={"device-trusted"},
            session_ttl=timedelta(minutes=15),
        )

    def test_sign_in_issues_short_lived_server_session(self):
        session = self.service.sign_in(
            SignInRequest("user@example.test", "correct", "device-trusted")
        )
        self.assertEqual(session.subject_id, "subject-123")
        self.assertEqual(session.device_id, "device-trusted")
        self.assertGreater(session.expires_at, session.issued_at)
        self.assertEqual(len(session.session_id), 43)

    def test_invalid_credentials_are_rejected(self):
        with self.assertRaises(AuthenticationError) as raised:
            self.service.sign_in(
                SignInRequest("user@example.test", "wrong", "device-trusted")
            )
        self.assertEqual(raised.exception.failure, AuthFailure.INVALID_CREDENTIALS)

    def test_untrusted_device_cannot_refresh(self):
        service = InMemoryIdentityService(
            verify_credential=lambda _identity, _credential: "subject-123",
            trusted_devices={"other-device"},
        )
        session = service.sign_in(
            SignInRequest("user@example.test", "correct", "device-untrusted")
        )
        with self.assertRaises(AuthenticationError) as raised:
            service.refresh(session)
        self.assertEqual(raised.exception.failure, AuthFailure.UNTRUSTED_DEVICE)

    def test_refresh_rotates_session_and_revokes_old_session(self):
        session = self.service.sign_in(
            SignInRequest("user@example.test", "correct", "device-trusted")
        )
        refreshed = self.service.refresh(session)
        self.assertNotEqual(refreshed.session_id, session.session_id)
        with self.assertRaises(AuthenticationError) as raised:
            self.service.refresh(session)
        self.assertEqual(raised.exception.failure, AuthFailure.REVOKED_SESSION)

    def test_explicit_revoke_blocks_refresh(self):
        session = self.service.sign_in(
            SignInRequest("user@example.test", "correct", "device-trusted")
        )
        self.service.revoke(session)
        with self.assertRaises(AuthenticationError) as raised:
            self.service.refresh(session)
        self.assertEqual(raised.exception.failure, AuthFailure.REVOKED_SESSION)

    def test_blocked_identity_cannot_sign_in(self):
        service = InMemoryIdentityService(
            verify_credential=lambda _identity, _credential: "blocked-subject",
            blocked_subjects={"blocked-subject"},
        )
        with self.assertRaises(AuthenticationError) as raised:
            service.sign_in(
                SignInRequest("blocked@example.test", "correct", "device-1")
            )
        self.assertEqual(raised.exception.failure, AuthFailure.BLOCKED_IDENTITY)

    def test_rate_limit_applies_before_unlimited_credential_attempts(self):
        service = InMemoryIdentityService(
            verify_credential=lambda _identity, _credential: None,
            max_sign_ins=2,
        )
        request = SignInRequest("user@example.test", "wrong", "device-1")
        for _ in range(2):
            with self.assertRaises(AuthenticationError) as raised:
                service.sign_in(request)
            self.assertEqual(raised.exception.failure, AuthFailure.INVALID_CREDENTIALS)

        with self.assertRaises(AuthenticationError) as raised:
            service.sign_in(request)
        self.assertEqual(raised.exception.failure, AuthFailure.RATE_LIMITED)


if __name__ == "__main__":
    unittest.main()
