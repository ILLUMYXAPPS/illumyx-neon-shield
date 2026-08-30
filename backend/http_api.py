"""Dependency-free JSON HTTP adapter for the Neon Shield auth service."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, SignInRequest


MAX_BODY_BYTES = 32_768


def _session_json(session):
    # Do not echo the raw device identifier back to clients.
    return {
        "session_id": session.session_id,
        "subject_id": session.subject_id,
        "issued_at": session.issued_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
    }


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        server_version = "NeonShieldAuth/1.0"

        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if status != 204:
                self.wfile.write(body)

        def _body(self) -> dict:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("content length required")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("invalid content length") from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise ValueError("request too large")
            value = json.loads(self.rfile.read(length))
            if not isinstance(value, dict):
                raise ValueError("JSON object required")
            return value

        def _token(self) -> str:
            value = self.headers.get("Authorization", "")
            scheme, _, token = value.partition(" ")
            if scheme.lower() != "bearer" or not token.strip():
                raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            return token.strip()

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
                            str(data["phone_identity"]) if data.get("phone_identity") is not None else None,
                        )
                    )
                    self._json(200, {"session": _session_json(session)})
                    return
                if self.path == "/v1/auth/refresh":
                    self._json(200, {"session": _session_json(service.refresh_token(self._token()))})
                    return
                if self.path == "/v1/auth/logout":
                    service.revoke_token(self._token())
                    self._json(204, {})
                    return
                self._json(404, {"error": "not_found"})
            except AuthenticationError as exc:
                self._json(401, {"error": exc.failure.value})
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
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
