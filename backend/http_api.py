"""Dependency-free JSON HTTP adapter for the Neon Shield auth service."""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, SignInRequest


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
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 32_768:
                raise ValueError("request size out of range")
            value = json.loads(self.rfile.read(length) or b"{}")
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

        def _error(self, exc):
            if isinstance(exc, AuthenticationError):
                status = 429 if exc.failure == AuthFailure.RATE_LIMITED else (
                    410 if exc.failure == AuthFailure.EXPIRED_SESSION else 401
                )
                self._json(status, {"error": exc.failure.value})
            elif isinstance(exc, (ValueError, json.JSONDecodeError)):
                self._json(400, {"error": "invalid_request"})
            else:
                self._json(503, {"error": "unavailable"})

        def do_GET(self) -> None:
            try:
                if self.path == "/health":
                    self._json(200, {"status": "ok", "service": "neon-shield-auth"})
                    return
                if self.path == "/v1/devices":
                    session = self._session()
                    self._json(200, {"devices": service.device_pairing.devices(session)})
                    return
                self._json(404, {"error": "not_found"})
            except Exception as exc:
                self._error(exc)

        def do_POST(self) -> None:
            try:
                data = self._body()
                if self.path == "/v1/auth/sign-in":
                    session = service.sign_in(SignInRequest(
                        str(data.get("identity", "")),
                        str(data.get("credential", "")),
                        str(data.get("device_id", "")),
                        str(data["phone_identity"]) if data.get("phone_identity") is not None else None,
                    ))
                    self._json(200, {"session": _session_json(session)})
                    return

                if self.path == "/v1/device-pairing/start":
                    result = service.device_pairing.start(
                        str(data.get("identity", "")),
                        str(data.get("credential", "")),
                        str(data.get("device_id", "")),
                        str(data.get("device_name", "")),
                    )
                    self._json(201, result)
                    return

                if self.path == "/v1/device-pairing/status":
                    self._json(200, {"status": service.device_pairing.status(
                        str(data.get("request_id", "")), str(data.get("pairing_secret", ""))
                    )})
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
                if self.path == "/v1/device-pairing/reject":
                    service.device_pairing.reject(session, str(data.get("request_id", "")))
                    self._json(200, {"status": "rejected"})
                    return
                if self.path == "/v1/device-pairing/approve":
                    self._json(200, service.device_pairing.approve(
                        session,
                        str(data.get("request_id", "")),
                        pairing_code=data.get("pairing_code"),
                    ))
                    return
                self._json(404, {"error": "not_found"})
            except Exception as exc:
                self._error(exc)

        def do_PATCH(self) -> None:
            try:
                match = re.fullmatch(r"/v1/devices/([A-Za-z0-9_-]{16,64})", self.path)
                if match is None:
                    self._json(404, {"error": "not_found"})
                    return
                session = self._session()
                data = self._body()
                service.device_pairing.rename(session, match.group(1), data.get("device_name"))
                self._json(200, {"updated": True})
            except Exception as exc:
                self._error(exc)

        def do_DELETE(self) -> None:
            try:
                match = re.fullmatch(r"/v1/devices/([A-Za-z0-9_-]{16,64})", self.path)
                if match is None:
                    self._json(404, {"error": "not_found"})
                    return
                session = self._session()
                service.device_pairing.unlink(session, match.group(1))
                self._json(204)
            except Exception as exc:
                self._error(exc)

        def log_message(self, format, *args) -> None:
            return

    return Handler


def serve(service, host: str = "127.0.0.1", port: int = 8080) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("bind behind an HTTPS reverse proxy for non-local deployment")
    ThreadingHTTPServer((host, port), make_handler(service)).serve_forever()
