"""Regression tests for bounded HTTP request parsing and JSON field validation."""
from __future__ import annotations

import socket
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from backend.http_api import (
    _MAX_REQUEST_BYTES,
    _parse_content_length,
    _sign_in_request,
    make_handler,
)


class HttpBoundaryValidationTests(unittest.TestCase):
    def test_content_length_accepts_zero_and_bounded_decimal(self):
        self.assertEqual(_parse_content_length("0"), 0)
        self.assertEqual(_parse_content_length("123"), 123)
        self.assertEqual(_parse_content_length(str(_MAX_REQUEST_BYTES)), _MAX_REQUEST_BYTES)

    def test_content_length_rejects_missing_malformed_negative_and_oversized_values(self):
        for value in (None, "", "-1", "+1", "1.5", "1x", "١"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _parse_content_length(value)
        with self.assertRaisesRegex(ValueError, "too large"):
            _parse_content_length(str(_MAX_REQUEST_BYTES + 1))

    def test_sign_in_payload_accepts_expected_string_fields(self):
        request = _sign_in_request({
            "identity": "user@example.test",
            "credential": "correct-horse",
            "device_id": "device-1",
            "phone_identity": "+61400000000",
        })
        self.assertEqual(request.identity, "user@example.test")
        self.assertEqual(request.credential, "correct-horse")
        self.assertEqual(request.device_id, "device-1")
        self.assertEqual(request.phone_identity, "+61400000000")

    def test_sign_in_payload_does_not_coerce_non_string_fields(self):
        valid = {
            "identity": "user@example.test",
            "credential": "correct-horse",
            "device_id": "device-1",
        }
        for field, value in (
            ("identity", {"unexpected": "object"}),
            ("identity", 123),
            ("credential", ["not", "a", "string"]),
            ("credential", None),
            ("device_id", True),
            ("phone_identity", 123),
        ):
            payload = dict(valid)
            payload[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    _sign_in_request(payload)

    def test_sign_in_payload_rejects_empty_and_overlong_values(self):
        valid = {
            "identity": "user@example.test",
            "credential": "correct-horse",
            "device_id": "device-1",
        }
        invalid_payloads = [
            {**valid, "identity": " "},
            {**valid, "identity": "i" * 321},
            {**valid, "credential": ""},
            {**valid, "credential": "c" * 4097},
            {**valid, "device_id": ""},
            {**valid, "device_id": "d" * 513},
            {**valid, "phone_identity": "p" * 65},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload_keys=tuple(payload)):
                with self.assertRaises(ValueError):
                    _sign_in_request(payload)

    def test_slow_request_body_times_out_and_closes_connection(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(object()))
        server.daemon_threads = True
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)

        with patch("backend.http_api._REQUEST_READ_TIMEOUT_SECONDS", 0.2):
            server_thread.start()
            try:
                with socket.create_connection(server.server_address, timeout=2) as client:
                    client.settimeout(2)
                    client.sendall(
                        b"POST /v1/auth/sign-in HTTP/1.1\r\n"
                        b"Host: localhost\r\n"
                        b"Content-Type: application/json\r\n"
                        b"Content-Length: 100\r\n"
                        b"\r\n"
                    )
                    response = client.recv(4096)
                self.assertIn(b"408 Request Timeout", response)
                self.assertIn(b"Connection: close", response)
                self.assertIn(b"request_timeout", response)
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
