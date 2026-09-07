import unittest

from backend.production_config import validate_production_config


class ProductionConfigTests(unittest.TestCase):
    def test_rejects_non_production_environment(self):
        with self.assertRaisesRegex(RuntimeError, "NEON_AUTH_ENV=production"):
            validate_production_config({})

    def test_rejects_missing_required_configuration(self):
        with self.assertRaisesRegex(RuntimeError, "NEON_AUTH_DB"):
            validate_production_config({"NEON_AUTH_ENV": "production"})

    def test_accepts_complete_runtime_configuration(self):
        env = {
            "NEON_AUTH_ENV": "production",
            "NEON_AUTH_DB": "postgresql://managed.example/neon",
            "NEON_IDP_URL": "https://idp.example",
            "NEON_IDP_CLIENT_ID": "test-client",
            "NEON_IDP_CLIENT_SECRET": "test-secret",
            "NEON_SESSION_SECRET": "test-session-secret",
            "NEON_MONITORING_ENDPOINT": "https://monitoring.example/events",
        }
        config = validate_production_config(env)
        self.assertEqual(config.database_url, env["NEON_AUTH_DB"])
        self.assertEqual(config.idp_url, env["NEON_IDP_URL"])


if __name__ == "__main__":
    unittest.main()
