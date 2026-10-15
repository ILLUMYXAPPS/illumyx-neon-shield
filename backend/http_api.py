"""Dependency-free JSON HTTP adapter for the Neon Shield auth service."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, SignInRequest


_MAX_REQUEST_BODY_BYTES = 32_768


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
        server_version = "NeonShieldAuth/1.0"

        def _json(self, status: int, payload: dict | None = None) -> None:
            body = b"" if status == 204 else json.dumps(payload or {}, separators=(",", ":")).encode()
            self.send_response(status)
            if status != 204:
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _body(self) -> dict:
            # This adapter accepts only a single, explicitly sized request body.
            # In particular, never let a negative length turn read() into an
            # unbounded read from the client socket.
            if self.headers.get("Transfer-Encoding") is not None:
                raise ValueError("transfer encoding is unsupported")

            content_lengths = self.headers.get_all("Content-Length", [])
            if len(content_lengths) > 1:
                raise ValueError("duplicate content length")

            raw_length = content_lengths[0] if content_lengths else "0"
            try:
                length = int(raw_length)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid content length") from exc

            if length < 0:
                raise ValueError("invalid content length")
            if length > _MAX_REQUEST_BODY_BYTES:
                raise ValueError("request too large")

            raw_body = self.rfile.read(length)
            if len(raw_body) != length:
                raise ValueError("incomplete request body")

            value = json.loads(raw_body or b"{}")
            if not isinstance(value, dict):
                raise ValueError("JSON object required")
            return value

        def _session(self):
            value = self.headers.get("Authorization", "")
            if not value.startswith("Bearer "):
                raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            token = value[7:].strip()
            if not token:
                raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            return service.resolve_session(token)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._json(200, {"status": "ok", "service": "neon-shield-auth"})
            else:
                self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            try:
                data = self._body()
                if self.path == "/v1/auth/sign-in":
                    session = service.sign_in(
                        SignInRequest(
                            str(data.get("identity", "")),
                            str(data.get("credential", "")),
                            str(data.get("device_id", "")),
                            str(data["phone_identity"])
                            if data.get("phone_identity") is not None
                            else None,
                        )
                    )
                    self._json(200, {"session": _session_json(session)})
                    return

                session = self._session()
                if self.path == "/v1/auth/refresh":
                    self._json(200, {"session": _session_json(service.refresh(session))})
                    return
                if self.path == "/v1/auth/logout":
                    service.revoke(session)
                    self._json(204)
                    return
                if self.path == "/v1/auth/trusted-device":
                    self._json(200, {"trusted": service.is_device_trusted(session)})
                    return
                self._json(404, {"error": "not_found"})
            except AuthenticationError as exc:
                self._json(401, {"error": exc.failure.value})
            except (ValueError, json.JSONDecodeError):
                self._json(400, {"error": "invalid_request"})
            except Exception:
                self._json(503, {"error": "unavailable"})

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def serve(service, host: str = "127.0.0.1", port: int = 8080) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("bind behind an HTTPS reverse proxy for non-local deployment")
    ThreadingHTTPServer((host, port), make_handler(service)).serve_forever()
