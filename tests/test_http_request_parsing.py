"""Regression tests for bounded HTTP request-body parsing."""
from email.message import Message
from io import BytesIO
import socket
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from backend.http_api import make_handler


class HttpRequestBodyParsingTests(unittest.TestCase):
    def setUp(self):
        self.handler_class = make_handler(service=object())

    def parse_body(self, headers, body=b""):
        handler = object.__new__(self.handler_class)
        handler.headers = Message()
        if "Content-Type" not in headers:
            handler.headers["Content-Type"] = "application/json"
        for name, value in headers.items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                handler.headers[name] = item
        handler.rfile = BytesIO(body)
        class FakeConnection:
            def settimeout(self, _timeout):
                pass
        handler.connection = FakeConnection()
        return handler._body()

    def test_valid_json_object_is_accepted(self):
        self.assertEqual(
            self.parse_body({"Content-Length": "7"}, b'{"a":1}'),
            {"a": 1},
        )

    def test_empty_body_defaults_to_empty_object(self):
        self.assertEqual(self.parse_body({"Content-Length": "0"}), {})

    def test_negative_content_length_is_rejected(self):
        with self.assertRaises(ValueError):
            self.parse_body({"Content-Length": "-1"}, b"ignored")

    def test_signed_content_length_is_rejected(self):
        for value in ("+2", "-0"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Content-Length"):
                    self.parse_body({"Content-Length": value}, b"{}")

    def test_whitespace_padded_content_length_is_rejected(self):
        for value in (" 2", "2 ", "\t2", "2\n"):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ValueError, "invalid content length"):
                    self.parse_body({"Content-Length": value}, b"{}")

    def test_non_ascii_decimal_content_length_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid content length"):
            self.parse_body({"Content-Length": "٢"}, b"{}")

    def test_duplicate_content_length_headers_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Content-Length"):
            self.parse_body(
                {"Content-Length": ["2", "3"]},
                b"{} ",
            )

    def test_non_numeric_content_length_is_rejected(self):
        with self.assertRaises(ValueError):
            self.parse_body({"Content-Length": "abc"})

    def test_oversized_body_is_rejected_before_reading(self):
        with self.assertRaisesRegex(ValueError, "too large"):
            self.parse_body({"Content-Length": "32769"})

    def test_truncated_body_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.parse_body({"Content-Length": "5"}, b"{}")

    def test_transfer_encoding_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Transfer-Encoding"):
            self.parse_body(
                {"Content-Length": "2", "Transfer-Encoding": "chunked"},
                b"{}",
            )

    def test_non_object_json_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            self.parse_body({"Content-Length": "2"}, b"[]")

    def test_trickled_request_body_hits_total_deadline(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(object()))
        server.daemon_threads = True
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)

        with patch("backend.http_api._REQUEST_BODY_DEADLINE_SECONDS", 0.35):
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

                    def trickle_body():
                        for _ in range(20):
                            try:
                                client.sendall(b"x")
                            except OSError:
                                return
                            time.sleep(0.08)

                    sender = threading.Thread(target=trickle_body, daemon=True)
                    sender.start()
                    response = bytearray()
                    while b"\r\n\r\n" not in response:
                        chunk = client.recv(4096)
                        if not chunk:
                            break
                        response.extend(chunk)
                    header_end = response.find(b"\r\n\r\n") + 4
                    headers = bytes(response[:header_end])
                    body = bytearray(response[header_end:])
                    content_length = next(
                        int(line.split(b":", 1)[1].strip())
                        for line in headers.split(b"\r\n")
                        if line.lower().startswith(b"content-length:")
                    )
                    while len(body) < content_length:
                        chunk = client.recv(4096)
                        if not chunk:
                            break
                        body.extend(chunk)
                    sender.join(timeout=1)
                self.assertIn(b"408 Request Timeout", headers)
                self.assertIn(b"Connection: close", headers)
                self.assertIn(b"request_timeout", body)
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
