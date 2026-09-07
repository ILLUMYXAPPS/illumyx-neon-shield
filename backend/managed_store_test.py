"""Contract tests for the production persistence boundary."""
from __future__ import annotations

import unittest

from backend.managed_store import ManagedAuthStore


class ManagedAuthStoreContractTest(unittest.TestCase):
    def test_contract_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            ManagedAuthStore()  # type: ignore[abstract]

    def test_required_operations_are_declared(self) -> None:
        required = {
            "create_user", "trust_device", "set_device_trusted", "block_phone",
            "find_user", "device_trusted", "device_hash_trusted", "identity_blocked",
            "phone_blocked", "save_session", "save_session_hash", "get_session",
            "revoke_session", "last_audit_hash", "add_audit", "add_audit_fingerprint",
        }
        self.assertTrue(required.issubset(set(ManagedAuthStore.__abstractmethods__)))


if __name__ == "__main__":
    unittest.main()
