import json
import threading
import unittest
from datetime import timedelta
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from backend.http_api import make_handler
from backend.service import PersistentIdentityService
from backend.store import AuthStore


class HttpApiTests(unittest.TestCase):
    def setUp(self):
        self.store = AuthStore(":memory:", pepper="test-pepper")
        self.store.create_user("subject-1", "user@example.test", "correct")
        self.store.trust_device("subject-1", "device-1")
        service = PersistentIdentityService(self.store, session_ttl=timedelta(minutes=15))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.store.close()

    def request(self, method, path, body=None, headers=None):
        payload = None if body is None else json.dumps(body)
        self.connection.request(method, path, body=payload, headers=headers or {})
        response = self.connection.getresponse()
        raw = response.read()
        return response, json.loads(raw) if raw else None

    def test_health(self):
        response, payload = self.request("GET", "/health")
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_sign_in_does_not_return_device_identifier(self):
        response, payload = self.request(
            "POST", "/v1/auth/sign-in",
            {"identity": "user@example.test", "credential": "correct", "device_id": "device-1"},
        )
        self.assertEqual(response.status, 200)
        self.assertNotIn("device_id", payload["session"])
        self.assertNotIn("device-1", json.dumps(payload))

    def test_refresh_requires_bearer_token(self):
        response, payload = self.request("POST", "/v1/auth/refresh", {}, {"Content-Type": "application/json"})
        self.assertEqual(response.status, 401)
        self.assertEqual(payload["error"], "invalid_credentials")

    def test_malformed_json_is_rejected(self):
        self.connection.request("POST", "/v1/auth/sign-in", body="{", headers={"Content-Type": "application/json", "Content-Length": "1"})
        response = self.connection.getresponse()
        self.assertEqual(response.status, 400)
        response.read()

    def test_unknown_route_is_not_found(self):
        response, payload = self.request("POST", "/v1/auth/nope", {})
        self.assertEqual(response.status, 404)
        self.assertEqual(payload["error"], "not_found")

    def test_logout_returns_no_body(self):
        response, _ = self.request("POST", "/v1/auth/logout", {}, {"Authorization": "Bearer invalid"})
        self.assertEqual(response.status, 401)


if __name__ == "__main__":
    unittest.main()
