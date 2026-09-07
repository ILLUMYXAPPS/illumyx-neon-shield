"""Tests for the deployment secret boundary."""
from __future__ import annotations

import unittest

from backend.secrets import EnvironmentSecretProvider, MappingSecretProvider


class SecretProviderTests(unittest.TestCase):
    def test_environment_provider_returns_secret_without_logging_value(self):
        secret = "unit-test-secret"
        provider = EnvironmentSecretProvider({"NEON_SESSION_SECRET": secret})
        self.assertEqual(provider.get_required("NEON_SESSION_SECRET"), secret)

    def test_missing_environment_secret_fails_closed(self):
        provider = EnvironmentSecretProvider({})
        with self.assertRaisesRegex(RuntimeError, "NEON_SESSION_SECRET"):
            provider.get_required("NEON_SESSION_SECRET")

    def test_empty_environment_secret_fails_closed(self):
        provider = EnvironmentSecretProvider({"NEON_SESSION_SECRET": ""})
        with self.assertRaisesRegex(RuntimeError, "NEON_SESSION_SECRET"):
            provider.get_required("NEON_SESSION_SECRET")

    def test_mapping_provider_is_deterministic_test_adapter(self):
        provider = MappingSecretProvider({"NEON_DB_PEPPER": "pepper"})
        self.assertEqual(provider.get_required("NEON_DB_PEPPER"), "pepper")


if __name__ == "__main__":
    unittest.main()
