"""HTTP tests for the authenticated store account binding route."""
from __future__ import annotations

import json
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, ServerSession
from backend.http_api import make_handler


class StoreBindingHttpApiTests(unittest.TestCase):
    def setUp(self):
        self.session = ServerSession(
            "valid-bearer-token",
            "server-resolved-subject",
            "trusted-device",
            datetime.now(timezone.utc),
            datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        self.binding_service = Mock()
        self.binding_service.get_or_create_for_session.return_value = "opaque-server-binding"
        self.service = Mock()
        self.service.resolve_session.return_value = self.session
        self.service.store_account_binding_service = self.binding_service
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.service))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1/store/account-binding"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, token="valid-bearer-token", body=None):
        payload = json.dumps(body or {}).encode()
        request = Request(
            self.url,
            data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        return urlopen(request, timeout=3)

    def test_returns_stable_binding_for_authenticated_session(self):
        with self.request() as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {"account_binding_id": "opaque-server-binding"})
        self.service.resolve_session.assert_called_once_with("valid-bearer-token")
        self.binding_service.get_or_create_for_session.assert_called_once_with(
            session_id="valid-bearer-token"
        )

    def test_client_subject_or_binding_fields_are_ignored(self):
        with self.request(body={
            "subject_id": "attacker-selected-subject",
            "account_binding_id": "attacker-selected-binding",
        }) as response:
            self.assertEqual(json.loads(response.read()), {"account_binding_id": "opaque-server-binding"})
        self.binding_service.get_or_create_for_session.assert_called_once_with(
            session_id="valid-bearer-token"
        )

    def test_missing_bearer_is_rejected(self):
        request = Request(self.url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, 401)

    def test_missing_binding_service_fails_closed(self):
        self.service.store_account_binding_service = None
        with self.assertRaises(HTTPError) as raised:
            self.request()
        self.assertEqual(raised.exception.code, 503)

    def test_expired_or_revoked_session_is_rejected(self):
        self.service.resolve_session.side_effect = AuthenticationError(AuthFailure.REVOKED_SESSION)
        with self.assertRaises(HTTPError) as raised:
            self.request()
        self.assertEqual(raised.exception.code, 401)
        self.binding_service.get_or_create_for_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
