import unittest

from device_security_panel import build_device_security_panel
from device_sessions import DeviceSession, DeviceSessionRegistry


class DeviceSecurityPanelTests(unittest.TestCase):
    def test_panel_counts_devices_and_sessions(self):
        registry = DeviceSessionRegistry()
        registry.add_or_update(DeviceSession("a", "Trusted", True, True, "app_session", "now"))
        registry.add_or_update(DeviceSession("b", "Unknown", False, True, "app_session", "now"))
        registry.add_or_update(DeviceSession("c", "Offline", True, False, "none", "earlier"))

        panel = build_device_security_panel(registry)
        self.assertEqual(panel["recognised_devices"], 2)
        self.assertEqual(panel["active_sessions"], 2)
        self.assertEqual(panel["unknown_devices"], 1)
        self.assertEqual(panel["actions"], ["view", "verify", "revoke_session"])


if __name__ == "__main__":
    unittest.main()
