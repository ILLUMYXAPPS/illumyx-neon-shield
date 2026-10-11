"""Tests for concrete production PostgreSQL store construction."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import Mock, patch

from backend.managed_db_store import ManagedDbAuthStore
from backend.managed_store import ManagedAuthStore
from backend.production_config import ProductionConfig
from backend.production_store_factory import build_managed_db_store
from backend.serialized_audit_store import SerializedAuditManagedDbAuthStore


class ProductionStoreFactoryTests(unittest.TestCase):
    def _config(self):
        return ProductionConfig(
            database_url="postgresql://managed.example/auth?sslmode=verify-full",
            database_user="neon_service",
            database_password="db-password-test-value",
            idp_url="https://idp.example",
            idp_client_id="client-id",
            idp_client_secret="idp-secret-test-value",
            database_pepper="db-pepper-test-value",
            monitoring_endpoint="https://monitor.example/events",
        )

    def test_constructs_managed_store_with_production_pepper_without_connecting(self):
        store = build_managed_db_store(self._config())
        self.assertIsInstance(store, ManagedDbAuthStore)
        self.assertIsInstance(store, SerializedAuditManagedDbAuthStore)
        self.assertIsInstance(store, ManagedAuthStore)
        self.assertEqual(store._pepper, "db-pepper-test-value")
        self.assertEqual(store._placeholder, "%s")
        self.assertEqual(store._audit_lock_clause, " FOR UPDATE")

    def test_connection_uses_separate_credentials_tls_url_and_bounded_timeout(self):
        connect = Mock(return_value=object())
        fake_driver = types.SimpleNamespace(connect=connect)
        with patch.dict(sys.modules, {"psycopg": fake_driver}):
            store = build_managed_db_store(self._config())
            connection = store._connection_factory()
        self.assertIsNotNone(connection)
        connect.assert_called_once_with(
            "postgresql://managed.example/auth?sslmode=verify-full",
            user="neon_service",
            password="db-password-test-value",
            connect_timeout=10,
            application_name="illumyx-neon-shield",
        )

    def test_rejects_database_url_with_embedded_credentials(self):
        config = self._config()
        config = ProductionConfig(
            database_url="postgresql://user:password@managed.example/auth?sslmode=verify-full",
            database_user=config.database_user,
            database_password=config.database_password,
            idp_url=config.idp_url,
            idp_client_id=config.idp_client_id,
            idp_client_secret=config.idp_client_secret,
            database_pepper=config.database_pepper,
            monitoring_endpoint=config.monitoring_endpoint,
        )
        with self.assertRaisesRegex(RuntimeError, "must not contain credentials"):
            build_managed_db_store(config)

    def test_rejects_missing_pepper(self):
        config = self._config()
        config = ProductionConfig(
            database_url=config.database_url,
            database_user=config.database_user,
            database_password=config.database_password,
            idp_url=config.idp_url,
            idp_client_id=config.idp_client_id,
            idp_client_secret=config.idp_client_secret,
            database_pepper="  ",
            monitoring_endpoint=config.monitoring_endpoint,
        )
        with self.assertRaisesRegex(RuntimeError, "pepper"):
            build_managed_db_store(config)


if __name__ == "__main__":
    unittest.main()
