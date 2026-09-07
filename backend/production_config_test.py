"""Tests for production configuration and secret-boundary enforcement."""
from __future__ import annotations

import unittest

from backend.production_config import validate_production_config
from backend.secrets import MappingSecretProvider


class ProductionConfigTests(unittest.TestCase):
    def _env(self):
        return {
            "NEON_AUTH_ENV": "production",
            "NEON_AUTH_DB": "postgresql://managed.example/auth",
            "NEON_IDP_URL": "https://idp.example",
            "NEON_IDP_CLIENT_ID": "client-id",
            "NEON_MONITORING_ENDPOINT": "https://monitor.example/events",
        }

    def _provider(self):
        return MappingSecretProvider({
            "NEON_IDP_CLIENT_SECRET": "idp-test-value",
            "NEON_SESSION_SECRET": "session-test-value",
            "NEON_DB_PEPPER": "pepper-test-value",
        })

    def test_production_config_resolves_secrets_through_provider(self):
        config = validate_production_config(self._env(), secret_provider=self._provider())
        self.assertEqual(config.idp_client_secret, "idp-test-value")
        self.assertEqual(config.session_secret, "session-test-value")
        self.assertEqual(config.database_pepper, "pepper-test-value")

    def test_missing_secret_fails_closed(self):
        provider = MappingSecretProvider({"NEON_IDP_CLIENT_SECRET": "idp-test-value"})
        with self.assertRaisesRegex(RuntimeError, "NEON_SESSION_SECRET"):
            validate_production_config(self._env(), secret_provider=provider)


if __name__ == "__main__":
    unittest.main()
