import tempfile
import unittest
from datetime import timedelta

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, SignInRequest
from backend.service import PersistentIdentityService
from backend.store import AuthStore, verify_secret


class PersistentBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.temp.close()
        self.store = AuthStore(self.temp.name, pepper="test-pepper")
        self.store.create_user("subject-1", "user@example.test", "correct")
        self.store.trust_device("subject-1", "device-1")
        self.service = PersistentIdentityService(self.store, session_ttl=timedelta(minutes=15), max_sign_ins=3)

    def tearDown(self):
        self.store.close()

    def test_password_record_is_not_plaintext(self):
        row = self.store.find_user("user@example.test")
        self.assertNotEqual(row["credential_record"], "correct")
        self.assertTrue(verify_secret("correct", row["credential_record"]))
        self.assertFalse(verify_secret("wrong", row["credential_record"]))

    def test_trusted_device_can_sign_in(self):
        session = self.service.sign_in(SignInRequest("user@example.test", "correct", "device-1"))
        self.assertEqual(session.subject_id, "subject-1")
        self.assertEqual(len(session.session_id), 43)
        self.assertGreater(session.expires_at, session.issued_at)

    def test_untrusted_device_is_denied(self):
        with self.assertRaises(AuthenticationError) as raised:
            self.service.sign_in(SignInRequest("user@example.test", "correct", "device-2"))
        self.assertEqual(raised.exception.failure, AuthFailure.UNTRUSTED_DEVICE)

    def test_refresh_rotates_opaque_token(self):
        first = self.service.sign_in(SignInRequest("user@example.test", "correct", "device-1"))
        second = self.service.refresh(first)
        self.assertNotEqual(first.session_id, second.session_id)
        with self.assertRaises(AuthenticationError) as raised:
            self.service.refresh(first)
        self.assertEqual(raised.exception.failure, AuthFailure.REVOKED_SESSION)

    def test_device_removal_blocks_refresh(self):
        session = self.service.sign_in(SignInRequest("user@example.test", "correct", "device-1"))
        self.store.set_device_trusted("subject-1", "device-1", False)
        with self.assertRaises(AuthenticationError) as raised:
            self.service.refresh(session)
        self.assertEqual(raised.exception.failure, AuthFailure.UNTRUSTED_DEVICE)

    def test_blocked_phone_is_denied(self):
        self.store.block_phone("+61400000000")
        with self.assertRaises(AuthenticationError) as raised:
            self.service.sign_in(SignInRequest("user@example.test", "correct", "device-1", "+61400000000"))
        self.assertEqual(raised.exception.failure, AuthFailure.BLOCKED_IDENTITY)

    def test_audit_chain_contains_no_raw_device_identifier(self):
        with self.assertRaises(AuthenticationError):
            self.service.sign_in(SignInRequest("user@example.test", "correct", "secret-device"))
        row = self.store._db.execute("SELECT * FROM audit_events ORDER BY rowid DESC LIMIT 1").fetchone()
        self.assertNotIn("secret-device", repr(dict(row)))
        self.assertEqual(len(row["event_hash"]), 64)
        self.assertEqual(len(row["device_fingerprint"]), 64)

    def test_failed_signins_rate_limit(self):
        request = SignInRequest("user@example.test", "wrong", "device-1")
        for _ in range(3):
            with self.assertRaises(AuthenticationError) as raised:
                self.service.sign_in(request)
            self.assertEqual(raised.exception.failure, AuthFailure.INVALID_CREDENTIALS)
        with self.assertRaises(AuthenticationError) as raised:
            self.service.sign_in(request)
        self.assertEqual(raised.exception.failure, AuthFailure.RATE_LIMITED)

    def test_malformed_password_record_is_rejected(self):
        self.store._db.execute("UPDATE users SET credential_record='pbkdf2_sha256$1$00$00'")
        self.assertFalse(verify_secret("correct", self.store.find_user("user@example.test")["credential_record"]))

    def test_refresh_rotation_is_atomic(self):
        first = self.service.sign_in(SignInRequest("user@example.test", "correct", "device-1"))
        self.store._db.execute("PRAGMA query_only=ON")
        with self.assertRaises(AuthenticationError):
            self.service.refresh(first)
        self.store._db.execute("PRAGMA query_only=OFF")
        row = self.store.get_session(first.session_id)
        self.assertEqual(row["revoked"], 0)


if __name__ == "__main__":
    unittest.main()
