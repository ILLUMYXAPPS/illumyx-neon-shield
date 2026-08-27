import unittest
from unittest.mock import patch

from neon_forensics import create_incident
from platform_collectors import collect_platform_telemetry, collect_windows_security_events


class PlatformCollectorTests(unittest.TestCase):
    def test_non_windows_windows_collector_is_noop(self):
        incident = create_incident()
        with patch("platform_collectors.platform.system", return_value="Linux"):
            self.assertEqual(collect_windows_security_events(incident), 0)
        self.assertEqual(incident.events, [])

    def test_current_host_dispatch_does_not_crash(self):
        incident = create_incident()
        with patch("platform_collectors.platform.system", return_value="Linux"):
            counts = collect_platform_telemetry(incident)
        self.assertEqual(counts, {"posture": 0, "events": 0, "processes": 0, "network": 0})

    def test_windows_event_xml_never_stores_command_line(self):
        incident = create_incident()
        xml = '<Event><System><EventID>4688</EventID><TimeCreated SystemTime="2026-08-26T10:00:00Z"/></System><EventData><Data Name="CommandLine">password=secret</Data></EventData></Event>'
        with patch("platform_collectors.platform.system", return_value="Windows"), patch("platform_collectors._run", return_value=xml), patch("platform_collectors.collect_windows_wfp_events", return_value=0):
            count = collect_windows_security_events(incident, max_events=1)
        self.assertEqual(count, 1)
        self.assertEqual(len(incident.events), 1)
        self.assertNotIn("command_line_arguments", incident.events[0].data)
        self.assertNotIn("password", str(incident.events[0].data))


if __name__ == "__main__":
    unittest.main()
