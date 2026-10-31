import json
import tempfile
import unittest
from pathlib import Path

from security.ip_evidence import (
    JsonlEvidenceSink,
    RequestEvidenceRecorder,
    resolve_client_ip,
)


class ResolveClientIpTests(unittest.TestCase):
    def test_ignores_forwarded_header_from_untrusted_peer(self):
        ip, source = resolve_client_ip("198.51.100.8", "203.0.113.9")
        self.assertEqual(ip, "198.51.100.8")
        self.assertEqual(source, "socket_peer")

    def test_uses_forwarded_chain_only_from_trusted_proxy(self):
        ip, source = resolve_client_ip(
            "10.0.0.2",
            "203.0.113.9, 10.0.0.1",
            trusted_proxy_cidrs=("10.0.0.0/8",),
        )
        self.assertEqual(ip, "203.0.113.9")
        self.assertEqual(source, "trusted_proxy_chain")

    def test_does_not_trust_spoofed_leftmost_ip_before_untrusted_hop(self):
        ip, _ = resolve_client_ip(
            "10.0.0.2",
            "192.0.2.123, 198.51.100.7",
            trusted_proxy_cidrs=("10.0.0.0/8",),
        )
        self.assertEqual(ip, "198.51.100.7")

    def test_invalid_peer_returns_unavailable(self):
        self.assertEqual(resolve_client_ip("not-an-ip")[0], None)


class RequestEvidenceRecorderTests(unittest.TestCase):
    def test_records_security_response_with_chain_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            sink = JsonlEvidenceSink(path)
            recorder = RequestEvidenceRecorder(
                sink, destination_domain="api.example.test"
            )
            digest = recorder.record(
                peer_ip="203.0.113.7",
                forwarded_for="",
                method="POST",
                status_code=403,
                user_agent="test-client",
            )
            self.assertEqual(len(digest), 64)
            saved = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(saved["data"]["source_ip"], "203.0.113.7")
            self.assertEqual(saved["data"]["http_status"], 403)
            self.assertNotIn("request_body", saved["data"])

    def test_ignores_non_security_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            recorder = RequestEvidenceRecorder(
                JsonlEvidenceSink(path), destination_domain="api.example.test"
            )
            self.assertIsNone(recorder.record(
                peer_ip="203.0.113.7", forwarded_for="", method="GET",
                status_code=200,
            ))
            self.assertFalse(path.exists())

    def test_detects_tampering_before_appending(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            recorder = RequestEvidenceRecorder(
                JsonlEvidenceSink(path), destination_domain="api.example.test"
            )
            recorder.record(
                peer_ip="203.0.113.7", forwarded_for="", method="GET",
                status_code=401,
            )
            path.write_text(path.read_text(encoding="utf-8").replace("203.0.113.7", "203.0.113.8"))
            with self.assertRaises(ValueError):
                JsonlEvidenceSink(path)


if __name__ == "__main__":
    unittest.main()
