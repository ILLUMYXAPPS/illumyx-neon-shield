import json
import tempfile
import unittest
from pathlib import Path

from neon_forensics import (
    CollectionClass,
    IncidentSeverity,
    SAFE_FIELDS,
    CONSENT_FIELDS,
    add_evidence,
    add_event,
    classify_field,
    create_incident,
    evidence_manifest,
    export_incident,
    filter_payload,
)


class NeonForensicsTests(unittest.TestCase):
    def test_safe_fields_are_accepted_without_consent(self):
        self.assertEqual(classify_field("source_ip"), CollectionClass.SAFE_TO_COLLECT)
        payload = filter_payload({"source_ip": "203.0.113.10", "destination_port": 443})
        self.assertEqual(payload["source_ip"], "203.0.113.10")

    def test_consent_fields_are_denied_without_consent(self):
        self.assertEqual(classify_field("screenshot"), CollectionClass.CONSENT_REQUIRED)
        payload = filter_payload({"screenshot": "bytes", "source_ip": "203.0.113.10"})
        self.assertNotIn("screenshot", payload)
        self.assertIn("source_ip", payload)

    def test_consent_fields_are_allowed_with_consent(self):
        payload = filter_payload({"screenshot": "bytes"}, consent_granted=True)
        self.assertEqual(payload["screenshot"], "bytes")

    def test_do_not_collect_fields_are_always_rejected(self):
        self.assertEqual(classify_field("raw_passwords"), CollectionClass.DO_NOT_COLLECT)
        payload = filter_payload({"raw_passwords": "secret", "source_ip": "203.0.113.10"}, consent_granted=True)
        self.assertNotIn("raw_passwords", payload)
        self.assertIn("source_ip", payload)

    def test_unknown_fields_fail_closed(self):
        self.assertEqual(classify_field("some_future_field"), CollectionClass.DO_NOT_COLLECT)
        payload = filter_payload({"some_future_field": "value"}, consent_granted=True)
        self.assertEqual(payload, {})

    def test_policy_classes_do_not_overlap(self):
        self.assertTrue(SAFE_FIELDS.isdisjoint(CONSENT_FIELDS))

    def test_endpoint_fields_require_consent(self):
        for field in ("source_endpoint", "destination_endpoint"):
            self.assertEqual(classify_field(field), CollectionClass.CONSENT_REQUIRED)
            self.assertNotIn(field, filter_payload({field: "endpoint"}))
            self.assertIn(field, filter_payload({field: "endpoint"}, consent_granted=True))

    def test_incident_event_is_correlated_and_severity_escalates(self):
        incident = create_incident(device_id="device-test")
        event = add_event(
            incident,
            event_type="failed_login",
            platform="windows",
            source="local_authentication",
            severity=IncidentSeverity.HIGH,
            confidence=0.85,
            data={"source_ip": "203.0.113.10", "destination_port": 443, "raw_passwords": "nope"},
        )
        self.assertEqual(event.data["source_ip"], "203.0.113.10")
        self.assertNotIn("raw_passwords", event.data)
        self.assertEqual(incident.severity, IncidentSeverity.HIGH)
        self.assertEqual(incident.confidence, 0.85)

    def test_evidence_hash_and_manifest(self):
        incident = create_incident()
        item = add_evidence(
            incident,
            b"hello evidence",
            source="user_selected_file",
            content_type="text/plain",
            classification=CollectionClass.USER_SUBMITTED,
            metadata={"user_selected_evidence": True, "raw_passwords": "blocked"},
        )
        self.assertEqual(len(item.sha256), 64)
        self.assertNotIn("raw_passwords", item.metadata)
        manifest = evidence_manifest(incident)
        self.assertEqual(manifest["entries"][0]["sha256"], item.sha256)
        self.assertEqual(len(manifest["manifest_sha256"]), 64)

    def test_manifest_hash_is_stable_across_regeneration(self):
        incident = create_incident()
        add_evidence(
            incident,
            b"stable evidence",
            source="user_selected_file",
            content_type="text/plain",
            classification=CollectionClass.USER_SUBMITTED,
        )
        first = evidence_manifest(incident)
        second = evidence_manifest(incident)
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["entries"], second["entries"])
        self.assertNotEqual(first["generated_at_utc"], "")
        self.assertNotEqual(second["generated_at_utc"], "")

    def test_export_writes_incident_and_manifest(self):
        incident = create_incident()
        add_event(
            incident,
            event_type="suspicious_connection",
            platform="macos",
            source="network_monitor",
            data={"destination_ip": "203.0.113.20"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = export_incident(incident, Path(tmp))
            incident_file = root / "incident.json"
            manifest_file = root / "manifest.json"
            self.assertTrue(incident_file.exists())
            self.assertTrue(manifest_file.exists())
            parsed = json.loads(incident_file.read_text(encoding="utf-8"))
            self.assertEqual(parsed["incident_id"], incident.incident_id)


if __name__ == "__main__":
    unittest.main()
