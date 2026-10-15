"""Dependency-free JSON HTTP adapter for the Neon Shield auth service."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, SignInRequest


_MAX_REQUEST_BYTES = 32_768
_MAX_IDENTITY_LENGTH = 320
_MAX_CREDENTIAL_LENGTH = 4_096
_MAX_DEVICE_ID_LENGTH = 512
_MAX_PHONE_IDENTITY_LENGTH = 64


def _parse_content_length(value: str | None) -> int:
    """Parse a bounded, non-negative decimal Content-Length without unbounded reads."""
    if value is None or not value or not value.isascii() or not value.isdecimal():
        raise ValueError("valid Content-Length required")
    length = int(value)
    if length > _MAX_REQUEST_BYTES:
        raise ValueError("request too large")
    return length


def _sign_in_request(data: dict) -> SignInRequest:
    """Validate untrusted JSON fields without coercing arbitrary values to strings."""
    identity = data.get("identity")
    credential = data.get("credential")
    device_id = data.get("device_id")
    phone_identity = data.get("phone_identity")

    if not isinstance(identity, str) or not identity.strip() or len(identity) > _MAX_IDENTITY_LENGTH:
        raise ValueError("invalid identity")
    if not isinstance(credential, str) or not credential or len(credential) > _MAX_CREDENTIAL_LENGTH:
        raise ValueError("invalid credential")
    if not isinstance(device_id, str) or not device_id or len(device_id) > _MAX_DEVICE_ID_LENGTH:
        raise ValueError("invalid device_id")
    if phone_identity is not None and (
        not isinstance(phone_identity, str)
        or not phone_identity.strip()
        or len(phone_identity) > _MAX_PHONE_IDENTITY_LENGTH
    ):
        raise ValueError("invalid phone_identity")

    return SignInRequest(identity, credential, device_id, phone_identity)


def _session_json(session):
    return {
        "session_id": session.session_id,
        "subject_id": session.subject_id,
        "device_id": session.device_id,
        "issued_at": session.issued_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
    }


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        server_version = "NeonShieldAuth"

        def _json(self, status: int, payload: dict | None = None) -> None:
            body = b"" if status == 204 else json.dumps(payload or {}, separators=(",", ":")).encode()
            self.send_response(status)
            if status != 204:
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _body(self) -> dict:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                raise ValueError("application/json required")
            length = _parse_content_length(self.headers.get("Content-Length"))
            raw_body = self.rfile.read(length) if length else b"{}"
            if len(raw_body) != length:
                raise ValueError("incomplete request body")
            value = json.loads(raw_body or b"{}")
            if not isinstance(value, dict):
                raise ValueError("JSON object required")
            return value

        def _session(self):
            value = self.headers.get("Authorization", "")
            scheme, separator, token = value.partition(" ")
            if not separator or scheme.lower() != "bearer" or not token.strip():
                raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            return service.resolve_session(token.strip())

        def do_GET(self) -> None:
            if self.path == "/health":
                self._json(200, {"status": "ok", "service": "neon-shield-auth"})
            else:
                self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            try:
                data = self._body()
                if self.path == "/v1/auth/sign-in":
                    session = service.sign_in(_sign_in_request(data))
                    self._json(200, {"session": _session_json(session)})
                    return

                if self.path not in {
                    "/v1/auth/refresh",
                    "/v1/auth/logout",
                    "/v1/auth/trusted-device",
                }:
                    self._json(404, {"error": "not_found"})
                    return

                session = self._session()
                if self.path == "/v1/auth/refresh":
                    self._json(200, {"session": _session_json(service.refresh(session))})
                    return
                if self.path == "/v1/auth/logout":
                    service.revoke(session)
                    self._json(204)
                    return
                self._json(200, {"trusted": service.is_device_trusted(session)})
            except AuthenticationError as exc:
                self._json(401, {"error": exc.failure.value})
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                self._json(400, {"error": "invalid_request"})
            except Exception:
                # Keep internal exceptions and credentials out of client responses.
                self._json(503, {"error": "unavailable"})

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def serve(service, host: str = "127.0.0.1", port: int = 8080) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("bind behind an HTTPS reverse proxy for non-local deployment")
    ThreadingHTTPServer((host, port), make_handler(service)).serve_forever()
