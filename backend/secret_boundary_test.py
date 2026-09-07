"""Regression tests for secret handling and leakage resistance."""
from __future__ import annotations

import unittest

from backend.production_config import validate_production_config
from backend.secrets import MappingSecretProvider


class SecretBoundaryTests(unittest.TestCase):
    _TEST_VALUES = ("fixture-one", "fixture-two", "fixture-three")

    def _env(self):
        return {
            "NEON_AUTH_ENV": "production",
            "NEON_AUTH_DB": "postgresql://managed.example/auth",
            "NEON_IDP_URL": "https://idp.example",
            "NEON_IDP_CLIENT_ID": "client-id",
            "NEON_MONITORING_ENDPOINT": "https://monitor.example/events",
        }

    def _provider(self):
        return MappingSecretProvider(dict(zip(
            ("NEON_IDP_CLIENT_SECRET", "NEON_SESSION_SECRET", "NEON_DB_PEPPER"),
            self._TEST_VALUES,
        )))

    def test_provider_is_required_by_production_config(self):
        with self.assertRaisesRegex(RuntimeError, "SecretProvider"):
            validate_production_config(self._env(), secret_provider=None)

    def test_empty_secret_fails_closed_without_echoing_values(self):
        provider = MappingSecretProvider({
            "NEON_IDP_CLIENT_SECRET": "",
            "NEON_SESSION_SECRET": self._TEST_VALUES[1],
            "NEON_DB_PEPPER": self._TEST_VALUES[2],
        })
        with self.assertRaisesRegex(RuntimeError, "NEON_IDP_CLIENT_SECRET") as error:
            validate_production_config(self._env(), secret_provider=provider)
        for value in self._TEST_VALUES:
            self.assertNotIn(value, str(error.exception))

    def test_production_config_repr_does_not_expose_secret_values(self):
        config = validate_production_config(self._env(), secret_provider=self._provider())
        rendered = repr(config)
        for value in self._TEST_VALUES:
            self.assertNotIn(value, rendered)


if __name__ == "__main__":
    unittest.main()
