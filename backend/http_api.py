"""Dependency-free JSON HTTP adapter for the Neon Shield auth service."""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, SignInRequest
from store_verification import StoreProvider, StorePurchaseRequest, StoreVerificationError, StoreVerificationUnavailable
from backend.family_invitations import FamilyInvitationError


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
            if length > 32_768:
                raise ValueError("request too large")
            value = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(value, dict):
                raise ValueError("JSON object required")
            return value

        def _error(self, exc: Exception) -> None:
            """Map expected request failures without exposing internal details."""
            if isinstance(exc, FamilyInvitationError):
                self._json(exc.status, {"error": exc.reason})
            elif isinstance(exc, AuthenticationError):
                self._json(401, {"error": exc.failure.value})
            elif isinstance(exc, StoreVerificationUnavailable):
                self._json(503, {"error": "store_verification_unavailable"})
            elif isinstance(exc, StoreVerificationError):
                self._json(400, {"error": "purchase_verification_failed"})
            elif isinstance(exc, (ValueError, json.JSONDecodeError)):
                self._json(400, {"error": "invalid_request"})
            else:
                self._json(503, {"error": "unavailable"})

        def _session(self):
            value = self.headers.get("Authorization", "")
            if not value.startswith("Bearer "):
                raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            token = value[7:].strip()
            if not token:
                raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            return service.resolve_session(token)

        def do_GET(self) -> None:
            try:
                if self.path == "/health":
                    self._json(200, {"status": "ok", "service": "neon-shield-auth"})
                    return
                if self.path == "/v1/family/invitations":
                    session = self._session()
                    family_invitations = getattr(service, "family_invitation_service", None)
                    if family_invitations is None:
                        self._json(503, {"error": "family_invitations_unavailable"})
                        return
                    self._json(200, {
                        "invitations": family_invitations.list_invitations(session.subject_id)
                    })
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

                if self.path == "/v1/store/apple/notifications":
                    processor = getattr(service, "apple_notification_processor", None)
                    if processor is None:
                        self._json(503, {"error": "apple_notifications_unavailable"})
                        return
                    signed_payload = data.get("signedPayload")
                    if not isinstance(signed_payload, str) or not signed_payload.strip():
                        raise ValueError("signedPayload is required")
                    inserted = processor.process(signed_payload)
                    self._json(200, {"status": "processed" if inserted else "duplicate"})
                    return

                if self.path == "/v1/store/google/rtdn":
                    processor = getattr(service, "google_rtdn_processor", None)
                    if processor is None:
                        self._json(503, {"error": "google_rtdn_unavailable"})
                        return
                    inserted = processor.process(
                        self.headers.get("Authorization", ""), data
                    )
                    self._json(200, {"status": "processed" if inserted else "duplicate"})
                    return

                session = self._session()
                family_invitations = getattr(service, "family_invitation_service", None)
                if self.path == "/v1/family/invitations":
                    if family_invitations is None:
                        self._json(503, {"error": "family_invitations_unavailable"})
                        return
                    self._json(201, family_invitations.create_invitation(session.subject_id))
                    return
                if self.path == "/v1/family/invitations/accept":
                    if family_invitations is None:
                        self._json(503, {"error": "family_invitations_unavailable"})
                        return
                    self._json(200, family_invitations.accept_invitation(
                        session.subject_id, str(data.get("invitation_code", ""))
                    ))
                    return
                if self.path == "/v1/store/account-binding":
                    binding_service = getattr(service, "store_account_binding_service", None)
                    if binding_service is None:
                        self._json(503, {"error": "unavailable"})
                        return
                    binding_id = binding_service.get_or_create_for_session(session_id=session.session_id)
                    self._json(200, {"account_binding_id": binding_id})
                    return

                if self.path == "/v1/store/verify-purchase":
                    verifier = getattr(service, "store_verification_service", None)
                    repository = getattr(service, "store_subscription_repository", None)
                    binding_service = getattr(service, "store_account_binding_service", None)
                    if verifier is None or repository is None or binding_service is None:
                        self._json(503, {"error": "unavailable"})
                        return
                    try:
                        provider = StoreProvider(str(data.get("provider", "")))
                    except ValueError as exc:
                        raise ValueError("unsupported provider") from exc
                    binding_id = binding_service.get_or_create_for_session(
                        session_id=session.session_id
                    )
                    purchase_request = StorePurchaseRequest(
                        provider=provider,
                        purchase_token=str(data.get("purchase_token", "")),
                        product_id=str(data.get("product_id", "")),
                        application_id=str(data.get("application_id", "")),
                        account_binding_id=binding_id,
                    )
                    snapshot = verifier.verify_and_persist(
                        purchase_request,
                        subject_id=session.subject_id,
                        expected_account_binding_id=binding_id,
                        repository=repository,
                    )
                    self._json(200, {
                        "package": snapshot.package.value,
                        "active": snapshot.active,
                        "expires_at": snapshot.expires_at.isoformat()
                        if snapshot.expires_at else None,
                    })
                    return
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

                if self.path == "/v1/device-pairing/approve":
                    self._json(200, service.device_pairing.approve(
                        session,
                        str(data.get("request_id", "")),
                        pairing_code=data.get("pairing_code"),
                    ))
                    return
                self._json(404, {"error": "not_found"})
            except FamilyInvitationError as exc:
                self._json(exc.status, {"error": exc.reason})
            except AuthenticationError as exc:
                self._json(401, {"error": exc.failure.value})
            except StoreVerificationUnavailable:
                self._json(503, {"error": "store_verification_unavailable"})
            except StoreVerificationError:
                self._json(400, {"error": "purchase_verification_failed"})
            except (ValueError, json.JSONDecodeError):
                self._json(400, {"error": "invalid_request"})
            except Exception:
                self._json(503, {"error": "unavailable"})

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
                invitation_match = re.fullmatch(r"/v1/family/invitations/([A-Za-z0-9_-]{16,64})", self.path)
                if invitation_match is not None:
                    session = self._session()
                    family_invitations = getattr(service, "family_invitation_service", None)
                    if family_invitations is None:
                        self._json(503, {"error": "family_invitations_unavailable"})
                        return
                    revoked = family_invitations.revoke_invitation(
                        session.subject_id, invitation_match.group(1)
                    )
                    self._json(200, {"revoked": revoked})
                    return
                match = re.fullmatch(r"/v1/devices/([A-Za-z0-9_-]{16,64})", self.path)
                if match is None:
                    self._json(404, {"error": "not_found"})
                    return
                session = self._session()
                service.device_pairing.unlink(session, match.group(1))
                self._json(204)
            except FamilyInvitationError as exc:
                self._json(exc.status, {"error": exc.reason})
            except Exception as exc:
                self._error(exc)

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def serve(service, host: str = "127.0.0.1", port: int = 8080) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("bind behind an HTTPS reverse proxy for non-local deployment")
    ThreadingHTTPServer((host, port), make_handler(service)).serve_forever()
