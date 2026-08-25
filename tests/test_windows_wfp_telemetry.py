import unittest
from unittest.mock import patch

from neon_forensics import IncidentSeverity, create_incident
from windows_wfp_telemetry import collect_windows_wfp_events


class WindowsWfpTelemetryTests(unittest.TestCase):
    def test_non_windows_is_noop(self):
        incident = create_incident()
        with patch("windows_wfp_telemetry.platform.system", return_value="Linux"):
            self.assertEqual(collect_windows_wfp_events(incident), 0)
        self.assertEqual(incident.events, [])

    def test_5156_and_5157_are_reduced_to_safe_metadata(self):
        xml = (
            '<Event><System><EventID>5156</EventID></System><EventData>'
            '<Data Name="SourceAddress">192.0.2.10</Data>'
            '<Data Name="DestAddress">198.51.100.20</Data>'
            '<Data Name="SourcePort">50123</Data>'
            '<Data Name="DestPort">443</Data>'
            '<Data Name="Protocol">6</Data>'
            '<Data Name="ProcessID">1234</Data>'
            '<Data Name="Application">C:\\Program Files\\Example\\app.exe</Data>'
            '<Data Name="Payload">secret-data</Data>'
            '</EventData></Event>'
            '<Event><System><EventID>5157</EventID></System><EventData>'
            '<Data Name="SourceAddress">192.0.2.10</Data>'
            '<Data Name="DestAddress">198.51.100.30</Data>'
            '<Data Name="DestPort">23</Data>'
            '<Data Name="Protocol">6</Data>'
            '</EventData></Event>'
        )
        incident = create_incident()
        with patch("windows_wfp_telemetry.platform.system", return_value="Windows"):
            count = collect_windows_wfp_events(incident, runner=lambda _cmd, _timeout: xml)
        self.assertEqual(count, 2)
        self.assertEqual(len(incident.events), 2)
        self.assertEqual(incident.events[0].data["destination_port"], "443")
        self.assertNotIn("Payload", incident.events[0].data)
        self.assertEqual(incident.events[1].severity, IncidentSeverity.MEDIUM)


if __name__ == "__main__":
    unittest.main()
