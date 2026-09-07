import unittest

from backend.production_config import validate_production_config


class ProductionConfigTests(unittest.TestCase):
    def test_rejects_non_production_environment(self):
        with self.assertRaisesRegex(RuntimeError, "NEON_AUTH_ENV=production"):
            validate_production_config({})

    def test_rejects_missing_required_configuration(self):
        with self.assertRaisesRegex(RuntimeError, "NEON_AUTH_DB"):
            validate_production_config({"NEON_AUTH_ENV": "production"})

    def test_rejects_local_sqlite_database(self):
        env = self._complete_env()
        env["NEON_AUTH_DB"] = "sqlite:///neon_shield.db"
        with self.assertRaisesRegex(RuntimeError, "managed durable database"):
            validate_production_config(env)

    def test_rejects_insecure_idp_endpoint(self):
        env = self._complete_env()
        env["NEON_IDP_URL"] = "http://idp.example"
        with self.assertRaisesRegex(RuntimeError, "HTTPS"):
            validate_production_config(env)

    def test_rejects_insecure_monitoring_endpoint(self):
        env = self._complete_env()
        env["NEON_MONITORING_ENDPOINT"] = "http://monitoring.example/events"
        with self.assertRaisesRegex(RuntimeError, "HTTPS"):
            validate_production_config(env)

    def test_accepts_complete_runtime_configuration(self):
        env = self._complete_env()
        config = validate_production_config(env)
        self.assertEqual(config.database_url, env["NEON_AUTH_DB"])
        self.assertEqual(config.idp_url, env["NEON_IDP_URL"])

    @staticmethod
    def _complete_env():
        return {
            "NEON_AUTH_ENV": "production",
            "NEON_AUTH_DB": "postgresql://managed.example/neon",
            "NEON_IDP_URL": "https://idp.example",
            "NEON_IDP_CLIENT_ID": "test-client",
            "NEON_IDP_CLIENT_SECRET": "test-secret",
            "NEON_SESSION_SECRET": "test-session-secret",
            "NEON_MONITORING_ENDPOINT": "https://monitoring.example/events",
        }


if __name__ == "__main__":
    unittest.main()
