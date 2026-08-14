import unittest
from unittest.mock import patch

import security_checks
from security_checks import CheckResult


class SecurityChecksTests(unittest.TestCase):
    def test_safe_check_converts_exception_to_info(self):
        def broken():
            raise RuntimeError("boom")

        result = security_checks._safe_check("Example", broken)
        self.assertEqual(result.name, "Example")
        self.assertEqual(result.result, "Unknown")
        self.assertEqual(result.state, "info")

    @patch("security_checks.shutil.disk_usage")
    def test_disk_check_warns_below_fifteen_percent(self, disk_usage):
        disk_usage.return_value = (100, 90, 10)
        result = security_checks._disk_check()
        self.assertEqual(result.state, "warn")
        self.assertEqual(result.result, "10.0%")

    @patch("security_checks.shutil.disk_usage")
    def test_disk_check_ok_at_fifteen_percent(self, disk_usage):
        disk_usage.return_value = (100, 85, 15)
        result = security_checks._disk_check()
        self.assertEqual(result.state, "ok")

    @patch("security_checks.platform.system", return_value="Windows")
    @patch("security_checks._powershell_command", return_value=None)
    def test_windows_firewall_without_powershell_is_unknown(self, _powershell, _system):
        result = security_checks._firewall_check()
        self.assertEqual(result.state, "info")
        self.assertEqual(result.result, "Unknown")

    @patch("security_checks.platform.system", return_value="Linux")
    @patch("security_checks.shutil.which", return_value=None)
    def test_linux_firewall_without_supported_tool_is_unknown(self, _which, _system):
        result = security_checks._firewall_check()
        self.assertEqual(result.state, "info")
        self.assertEqual(result.result, "Unknown")

    def test_run_local_checks_returns_check_results(self):
        results = security_checks.run_local_checks()
        self.assertTrue(results)
        self.assertTrue(all(isinstance(item, CheckResult) for item in results))
        self.assertTrue(all(item.state in {"ok", "warn", "info"} for item in results))


if __name__ == "__main__":
    unittest.main()
