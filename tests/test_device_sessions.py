import unittest

from device_sessions import DeviceSession, DeviceSessionRegistry


class DeviceSessionTests(unittest.TestCase):
    def test_active_session_is_visible(self):
        registry = DeviceSessionRegistry()
        registry.add_or_update(
            DeviceSession(
                device_id="device-1",
                device_name="Recognised Device",
                recognised=True,
                active=True,
                connection_type="app_session",
                last_seen="2026-08-21T00:00:00+00:00",
            )
        )
        self.assertEqual(len(registry.active_sessions()), 1)
        self.assertEqual(registry.summary()[0]["mirroring_status"], "active_session")

    def test_inactive_session_reports_none_detected(self):
        registry = DeviceSessionRegistry()
        registry.add_or_update(
            DeviceSession(
                device_id="device-2",
                device_name="Offline Device",
                recognised=True,
                active=False,
                connection_type="none",
                last_seen="2026-08-21T00:00:00+00:00",
            )
        )
        self.assertEqual(registry.active_sessions(), [])
        self.assertEqual(registry.summary()[0]["mirroring_status"], "none_detected")

    def test_update_replaces_existing_device(self):
        registry = DeviceSessionRegistry()
        base = dict(
            device_id="device-3",
            device_name="Test Device",
            recognised=True,
            connection_type="app_session",
            last_seen="2026-08-21T00:00:00+00:00",
        )
        registry.add_or_update(DeviceSession(active=False, **base))
        registry.add_or_update(DeviceSession(active=True, **base))
        self.assertEqual(len(registry.summary()), 1)
        self.assertTrue(registry.summary()[0]["active"])


if __name__ == "__main__":
    unittest.main()
