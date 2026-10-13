"""Regression tests for consistent session device identity across refresh."""
from __future__ import annotations

import unittest

from auth_server_contract import SignInRequest
from backend.service import PersistentIdentityService
from backend.store import AuthStore


class SessionDeviceIdentityTests(unittest.TestCase):
    def test_sign_in_and_refresh_return_same_stored_device_fingerprint(self) -> None:
        store = AuthStore(":memory:", pepper="test-pepper")
        try:
            store.create_user("subject-1", "user@example.test", "correct-password")
            store.trust_device("subject-1", "device-1")
            service = PersistentIdentityService(store)

            signed_in = service.sign_in(
                SignInRequest("user@example.test", "correct-password", "device-1")
            )
            stored = store.get_session(signed_in.session_id)
            self.assertIsNotNone(stored)
            self.assertEqual(signed_in.device_id, stored["device_hash"])
            self.assertNotEqual(signed_in.device_id, "device-1")

            refreshed = service.refresh_token(signed_in.session_id)
            refreshed_stored = store.get_session(refreshed.session_id)
            self.assertIsNotNone(refreshed_stored)
            self.assertEqual(refreshed.device_id, signed_in.device_id)
            self.assertEqual(refreshed.device_id, refreshed_stored["device_hash"])
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
