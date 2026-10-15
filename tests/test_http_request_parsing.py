"""Regression tests for bounded HTTP request-body parsing."""
from email.message import Message
from io import BytesIO
import unittest

from backend.http_api import make_handler


class HttpRequestBodyParsingTests(unittest.TestCase):
    def setUp(self):
        self.handler_class = make_handler(service=object())

    def parse_body(self, headers, body=b""):
        handler = object.__new__(self.handler_class)
        handler.headers = Message()
        for name, value in headers.items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                handler.headers[name] = item
        handler.rfile = BytesIO(body)
        return handler._body()

    def test_valid_json_object_is_accepted(self):
        self.assertEqual(
            self.parse_body({"Content-Length": "7"}, b'{"a":1}'),
            {"a": 1},
        )

    def test_empty_body_defaults_to_empty_object(self):
        self.assertEqual(self.parse_body({}), {})

    def test_negative_content_length_is_rejected(self):
        with self.assertRaises(ValueError):
            self.parse_body({"Content-Length": "-1"}, b"ignored")

    def test_signed_content_length_is_rejected(self):
        for value in ("+2", "-0"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid content length"):
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
        with self.assertRaisesRegex(ValueError, "duplicate content length"):
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
        with self.assertRaisesRegex(ValueError, "transfer encoding"):
            self.parse_body(
                {"Content-Length": "2", "Transfer-Encoding": "chunked"},
                b"{}",
            )

    def test_non_object_json_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            self.parse_body({"Content-Length": "2"}, b"[]")


if __name__ == "__main__":
    unittest.main()
