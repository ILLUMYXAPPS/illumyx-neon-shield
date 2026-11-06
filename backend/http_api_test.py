"""Regression tests for bounded HTTP request parsing and JSON field validation."""
from __future__ import annotations

import unittest

from backend.http_api import (
    _MAX_REQUEST_BYTES,
    _parse_content_length,
    _sign_in_request,
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


if __name__ == "__main__":
    unittest.main()
