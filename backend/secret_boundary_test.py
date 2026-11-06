"""Regression tests for secret handling and leakage resistance."""
from __future__ import annotations

import unittest

from backend.production_config import validate_production_config
from backend.secrets import EnvironmentSecretProvider, MappingSecretProvider


class SecretBoundaryTests(unittest.TestCase):
    _TEST_VALUES = ("fixture-one", "fixture-two")

    def _env(self):
        return {
            "NEON_AUTH_ENV": "production",
            "NEON_AUTH_DB": "postgresql://managed.example/auth?sslmode=verify-full",
            "NEON_IDP_URL": "https://idp.example",
            "NEON_IDP_CLIENT_ID": "client-id",
            "NEON_MONITORING_ENDPOINT": "https://monitor.example/events",
        }

    def _provider(self):
        return MappingSecretProvider(dict(zip(
            ("NEON_IDP_CLIENT_SECRET", "NEON_DB_PEPPER"),
            self._TEST_VALUES,
        )))

    def test_provider_is_required_by_production_config(self):
        with self.assertRaisesRegex(RuntimeError, "SecretProvider"):
            validate_production_config(self._env(), secret_provider=None)

    def test_empty_secret_fails_closed_without_echoing_values(self):
        provider = MappingSecretProvider({
            "NEON_IDP_CLIENT_SECRET": "",
            "NEON_DB_PEPPER": self._TEST_VALUES[1],
        })
        with self.assertRaisesRegex(RuntimeError, "NEON_IDP_CLIENT_SECRET") as error:
            validate_production_config(self._env(), secret_provider=provider)
        for value in self._TEST_VALUES:
            self.assertNotIn(value, str(error.exception))

    def test_whitespace_only_secrets_fail_closed_without_echoing_values(self):
        for name in ("NEON_IDP_CLIENT_SECRET", "NEON_DB_PEPPER"):
            with self.subTest(name=name):
                provider = MappingSecretProvider({
                    "NEON_IDP_CLIENT_SECRET": self._TEST_VALUES[0],
                    "NEON_DB_PEPPER": self._TEST_VALUES[1],
                    name: " \t\n ",
                })
                with self.assertRaisesRegex(RuntimeError, name) as error:
                    validate_production_config(self._env(), secret_provider=provider)
                for value in self._TEST_VALUES:
                    self.assertNotIn(value, str(error.exception))

    def test_environment_provider_rejects_whitespace_only_secret(self):
        provider = EnvironmentSecretProvider({"SAMPLE_SECRET": "  \t "})
        with self.assertRaisesRegex(RuntimeError, "SAMPLE_SECRET"):
            provider.get_required("SAMPLE_SECRET")

    def test_secret_values_are_preserved_not_trimmed(self):
        provider = MappingSecretProvider({"SAMPLE_SECRET": "  valid-value  "})
        self.assertEqual(provider.get_required("SAMPLE_SECRET"), "  valid-value  ")

    def test_production_config_repr_does_not_expose_secret_values(self):
        config = validate_production_config(self._env(), secret_provider=self._provider())
        rendered = repr(config)
        for value in self._TEST_VALUES:
            self.assertNotIn(value, rendered)


if __name__ == "__main__":
    unittest.main()
