"""Tests for production configuration and secret-boundary enforcement."""
from __future__ import annotations

import unittest

from backend.production_config import validate_production_config
from backend.secrets import MappingSecretProvider


class ProductionConfigTests(unittest.TestCase):
    def _env(self):
        return {
            "NEON_AUTH_ENV": "production",
            "NEON_AUTH_DB": "postgresql://managed.example/auth?sslmode=verify-full",
            "NEON_IDP_URL": "https://idp.example",
            "NEON_IDP_CLIENT_ID": "client-id",
            "NEON_MONITORING_ENDPOINT": "https://monitor.example/events",
        }

    def _provider(self):
        return MappingSecretProvider({
            "NEON_IDP_CLIENT_SECRET": "idp-test-value",
            "NEON_DB_PEPPER": "pepper-test-value",
        })

    def test_production_config_resolves_secrets_through_provider(self):
        config = validate_production_config(self._env(), secret_provider=self._provider())
        self.assertEqual(config.idp_client_secret, "idp-test-value")
        self.assertEqual(config.database_pepper, "pepper-test-value")
        self.assertNotIn("session_secret", config.__dataclass_fields__)

    def test_database_tls_is_required(self):
        env = self._env()
        env["NEON_AUTH_DB"] = "postgresql://managed.example/auth"
        with self.assertRaisesRegex(RuntimeError, "must explicitly require TLS"):
            validate_production_config(env, secret_provider=self._provider())

    def test_database_tls_rejects_invalid_sslmode(self):
        env = self._env()
        env["NEON_AUTH_DB"] = "postgresql://managed.example/auth?sslmode=disable"
        with self.assertRaisesRegex(RuntimeError, "must explicitly require TLS"):
            validate_production_config(env, secret_provider=self._provider())

    def test_non_postgresql_database_is_rejected(self):
        env = self._env()
        env["NEON_AUTH_DB"] = "mysql://managed.example/auth?sslmode=require"
        with self.assertRaisesRegex(RuntimeError, "must use a PostgreSQL connection URL"):
            validate_production_config(env, secret_provider=self._provider())

    def test_missing_secret_fails_closed(self):
        provider = MappingSecretProvider({"NEON_IDP_CLIENT_SECRET": "idp-test-value"})
        with self.assertRaisesRegex(RuntimeError, "NEON_DB_PEPPER"):
            validate_production_config(self._env(), secret_provider=provider)


if __name__ == "__main__":
    unittest.main()
