"""Regression tests for secret handling and leakage resistance."""
from __future__ import annotations

import unittest

from backend.production_config import validate_production_config
from backend.secrets import MappingSecretProvider


class SecretBoundaryTests(unittest.TestCase):
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
            "NEON_IDP_CLIENT_SECRET": "client-secret-test-only",
            "NEON_SESSION_SECRET": "session-secret-test-only",
            "NEON_DB_PEPPER": "database-pepper-test-only",
        })

    def test_provider_is_required_by_production_config(self):
        with self.assertRaisesRegex(RuntimeError, "SecretProvider"):
            validate_production_config(self._env())

    def test_empty_secret_fails_closed_without_echoing_value(self):
        provider = MappingSecretProvider({
            "NEON_IDP_CLIENT_SECRET": "",
            "NEON_SESSION_SECRET": "session-secret-test-only",
            "NEON_DB_PEPPER": "database-pepper-test-only",
        })
        with self.assertRaisesRegex(RuntimeError, "NEON_IDP_CLIENT_SECRET") as error:
            validate_production_config(self._env(), secret_provider=provider)
        self.assertNotIn("session-secret-test-only", str(error.exception))
        self.assertNotIn("database-pepper-test-only", str(error.exception))

    def test_production_config_repr_does_not_expose_secret_values(self):
        provider = self._provider()
        config = validate_production_config(self._env(), secret_provider=provider)
        rendered = repr(config)
        for secret in provider._values.values():
            self.assertNotIn(secret, rendered)


if __name__ == "__main__":
    unittest.main()
