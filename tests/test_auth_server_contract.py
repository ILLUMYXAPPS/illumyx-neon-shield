import unittest
from datetime import datetime, timezone

from auth_server_contract import AuthFailure, ServerSession, SignInRequest


class AuthServerContractTests(unittest.TestCase):
    def test_sign_in_request_keeps_identity_and_device_boundary(self):
        request = SignInRequest(
            identity="user@example.test",
            credential="credential-is-never-logged",
            device_id="device-123",
        )
        self.assertEqual(request.identity, "user@example.test")
        self.assertEqual(request.device_id, "device-123")

    def test_server_session_contains_server_authoritative_fields(self):
        issued = datetime.now(timezone.utc)
        expires = issued.replace(microsecond=0)
        session = ServerSession(
            session_id="server-session-id",
            subject_id="subject-123",
            device_id="device-123",
            issued_at=issued,
            expires_at=expires,
        )
        self.assertEqual(session.session_id, "server-session-id")
        self.assertEqual(session.subject_id, "subject-123")
        self.assertEqual(session.device_id, "device-123")

    def test_failure_taxonomy_covers_security_boundary(self):
        self.assertEqual(
            {failure.value for failure in AuthFailure},
            {
                "invalid_credentials",
                "expired_session",
                "revoked_session",
                "untrusted_device",
                "blocked_identity",
                "rate_limited",
                "unavailable",
            },
        )


if __name__ == "__main__":
    unittest.main()
