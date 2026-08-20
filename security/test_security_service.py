import unittest

from .access_control import AccessControl
from .security_service import SecurityService


class SecurityServiceTests(unittest.TestCase):
    def test_snapshot_reports_security_state(self):
        service = SecurityService(AccessControl())
        snapshot = service.snapshot()
        self.assertFalse(snapshot.owner_initialized)
        self.assertEqual(snapshot.trusted_device_count, 0)
        self.assertEqual(snapshot.audit_event_count, 0)

    def test_owner_controls_trusted_devices_through_service(self):
        service = SecurityService(AccessControl())
        salt = b"test-salt"
        service.initialize_owner("owner-secret", salt)
        service.add_trusted_device("owner-secret", salt, "device-1")

        self.assertTrue(service.is_trusted_device("device-1"))
        self.assertEqual(service.snapshot().trusted_device_count, 1)

    def test_invalid_owner_cannot_change_trusted_devices(self):
        service = SecurityService(AccessControl())
        salt = b"test-salt"
        service.initialize_owner("owner-secret", salt)

        with self.assertRaises(PermissionError):
            service.add_trusted_device("wrong-secret", salt, "device-1")

        self.assertFalse(service.is_trusted_device("device-1"))
        self.assertFalse(service.audit_events()[-1].success)

    def test_service_does_not_allow_reinitialization(self):
        service = SecurityService(AccessControl())
        salt = b"test-salt"
        service.initialize_owner("owner-secret", salt)

        with self.assertRaises(PermissionError):
            service.initialize_owner("replacement-secret", salt)

        self.assertTrue(service.verify_owner("owner-secret", salt))
        self.assertFalse(service.verify_owner("replacement-secret", salt))


if __name__ == "__main__":
    unittest.main()
