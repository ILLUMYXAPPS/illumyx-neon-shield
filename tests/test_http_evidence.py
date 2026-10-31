"""HTTP adapter integration tests for the optional intrusion evidence ledger."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure
from backend.http_api import make_handler


class RecordingEvidence:
    def __init__(self):
        self.events = []

    def record_event(self, **event):
        self.events.append(event)


class BrokenEvidence:
    def record_event(self, **event):
        raise OSError("evidence storage unavailable")


class FakeService:
    def sign_in(self, request):
        raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)


class HttpEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.evidence = RecordingEvidence()
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_handler(FakeService(), evidence_store=self.evidence),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, method="GET", body=None, headers=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = Request(self.base + path, data=data, method=method, headers=headers or {})
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, response.read()
        except HTTPError as exc:
            return exc.code, exc.read()

    def test_failed_sign_in_records_minimal_metadata_only(self):
        status, body = self.request(
            "/v1/auth/sign-in?tracking=do-not-store",
            method="POST",
            body={"identity": "person@example.test", "credential": "top-secret-password",
                  "device_id": "device-secret"},
            headers={"Content-Type": "application/json", "User-Agent": "NeonShieldTest/1"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error"], "invalid_credentials")
        self.assertEqual(len(self.evidence.events), 1)
        event = self.evidence.events[0]
        self.assertEqual(event["event_type"], "auth.failure")
        self.assertEqual(event["status_code"], 401)
        self.assertEqual(event["path"], "/v1/auth/sign-in")
        self.assertEqual(event["source_ip"], "127.0.0.1")
        self.assertEqual(event["user_agent"], "NeonShieldTest/1")
        serialized = json.dumps(event)
        for secret in ("top-secret-password", "person@example.test", "device-secret", "do-not-store"):
            self.assertNotIn(secret, serialized)

    def test_untrusted_forwarded_for_is_ignored(self):
        status, _ = self.request(
            "/missing",
            headers={"X-Forwarded-For": "198.51.100.77"},
        )
        self.assertEqual(status, 404)
        self.assertEqual(self.evidence.events[0]["source_ip"], "127.0.0.1")

    def test_invalid_json_is_recorded_as_bad_request(self):
        req = Request(self.base + "/v1/auth/sign-in", data=b"{", method="POST",
                      headers={"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(req, timeout=3)
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(self.evidence.events[0]["event_type"], "http.invalid_request")

    def test_evidence_store_failure_does_not_change_auth_response(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_handler(FakeService(), evidence_store=BrokenEvidence()),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_port
        status, body = self.request(
            "/v1/auth/sign-in", method="POST",
            body={"identity": "user", "credential": "secret", "device_id": "device"},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error"], "invalid_credentials")


if __name__ == "__main__":
    unittest.main()
