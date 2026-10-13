"""Tests for the explicit production migration deployment command."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from backend.production_config import MigrationConfig
from backend.run_production_migrations import main, run_migrations
from backend.secrets import MappingSecretProvider


class ProductionMigrationCommandTests(unittest.TestCase):
    def _env(self):
        return {
            "NEON_AUTH_ENV": "production",
            "NEON_AUTH_DB": "postgresql://managed.example/auth?sslmode=verify-full",
            "NEON_DB_USER": "neon_service",
        }

    def _provider(self):
        return MappingSecretProvider({"NEON_DB_PASSWORD": "test-db-password"})

    def _config(self):
        return MigrationConfig(
            database_url="postgresql://managed.example/auth?sslmode=verify-full",
            database_user="neon_service",
            database_password="test-db-password",
        )

    def test_requires_production_environment(self):
        with self.assertRaisesRegex(RuntimeError, "NEON_AUTH_ENV=production"):
            run_migrations(
                env={"NEON_AUTH_ENV": "development"},
                secret_provider=self._provider(),
                connection_factory=Mock(),
            )

    def test_configuration_validation_happens_before_opening_database(self):
        connect = Mock()
        with self.assertRaisesRegex(RuntimeError, "NEON_AUTH_ENV=production"):
            run_migrations(env={}, secret_provider=self._provider(), connection_factory=connect)
        connect.assert_not_called()

    def test_migration_command_requires_only_database_configuration(self):
        # Identity-provider, monitoring, and pepper settings are unrelated to
        # applying schema migrations and must not block this standalone job.
        with patch("backend.run_production_migrations.MigrationRunner") as runner_type:
            runner = runner_type.return_value
            runner.apply_pending.return_value = 4
            runner.current_version.return_value = 4
            connect = Mock()
            self.assertEqual(
                run_migrations(env=self._env(), secret_provider=self._provider(), connection_factory=connect),
                4,
            )
            connect.assert_not_called()
            runner_type.assert_called_once()

    def test_connection_factory_is_lazy_when_configuration_is_injected(self):
        with patch("backend.run_production_migrations.MigrationRunner") as runner_type:
            runner = runner_type.return_value
            runner.apply_pending.return_value = 4
            runner.current_version.return_value = 4
            connect = Mock()
            self.assertEqual(run_migrations(config=self._config(), connection_factory=connect), 4)
            connect.assert_not_called()
            runner_type.assert_called_once()

    def test_main_fails_closed_without_printing_driver_exception_details(self):
        with patch("backend.run_production_migrations.run_migrations", side_effect=RuntimeError("password=do-not-print")):
            with patch("sys.stderr") as stderr:
                self.assertEqual(main(), 1)
                message = "".join(call.args[0] for call in stderr.write.call_args_list)
                self.assertIn("RuntimeError", message)
                self.assertNotIn("do-not-print", message)


if __name__ == "__main__":
    unittest.main()
