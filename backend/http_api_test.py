"""HTTP tests for the authenticated store account binding route."""
from __future__ import annotations

import json
import threading
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, ServerSession
from backend.http_api import make_handler
from entitlements import Package
from store_verification import StoreVerificationError


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
        self.binding_service.get_or_create_for_session.return_value = "8e03978e-40d5-43e8-bc93-6894a57f9324"
        self.store_verifier = Mock()
        self.store_verifier.verify_and_persist.return_value = SimpleNamespace(
            package=Package.PREMIUM, active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.subscription_repository = Mock()
        self.service = Mock()
        self.service.resolve_session.return_value = self.session
        self.service.store_account_binding_service = self.binding_service
        self.service.store_verification_service = self.store_verifier
        self.service.store_subscription_repository = self.subscription_repository
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.service))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.url = self.base_url + "/v1/store/account-binding"

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
            self.assertEqual(json.loads(response.read()), {"account_binding_id": "8e03978e-40d5-43e8-bc93-6894a57f9324"})
        self.service.resolve_session.assert_called_once_with("valid-bearer-token")
        self.binding_service.get_or_create_for_session.assert_called_once_with(
            session_id="valid-bearer-token"
        )

    def test_client_subject_or_binding_fields_are_ignored(self):
        with self.request(body={
            "subject_id": "attacker-selected-subject",
            "account_binding_id": "attacker-selected-binding",
        }) as response:
            self.assertEqual(json.loads(response.read()), {"account_binding_id": "8e03978e-40d5-43e8-bc93-6894a57f9324"})
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

    def test_purchase_verification_uses_server_derived_binding(self):
        request = Request(
            self.base_url + "/v1/store/verify-purchase",
            data=json.dumps({
                "provider": "apple",
                "purchase_token": "signed-transaction-jws",
                "product_id": "premium.monthly",
                "application_id": "com.illumyx.illumyxapp",
                "account_binding_id": "attacker-chosen-binding",
                "subject_id": "attacker-chosen-subject",
            }).encode(),
            headers={"Authorization": "Bearer valid-bearer-token", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=3) as response:
            result = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(result["package"], "premium")
            self.assertTrue(result["active"])
        args = self.store_verifier.verify_and_persist.call_args.kwargs
        self.assertEqual(args["subject_id"], "server-resolved-subject")
        self.assertEqual(args["expected_account_binding_id"], "8e03978e-40d5-43e8-bc93-6894a57f9324")
        self.assertEqual(args["request"].account_binding_id, args["expected_account_binding_id"])
        self.assertIs(args["repository"], self.subscription_repository)

    def test_apple_notifications_endpoint_uses_verified_processor_without_customer_bearer(self):
        processor = Mock()
        processor.process.return_value = True
        self.service.apple_notification_processor = processor
        request = Request(
            self.base_url + "/v1/store/apple/notifications",
            data=json.dumps({"signedPayload": "signed.apple.notification"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {"status": "processed"})
        processor.process.assert_called_once_with("signed.apple.notification")
        self.service.resolve_session.assert_not_called()

    def test_apple_notifications_endpoint_fails_closed_when_unconfigured(self):
        self.service.apple_notification_processor = None
        request = Request(
            self.base_url + "/v1/store/apple/notifications",
            data=b'{"signedPayload":"signed.apple.notification"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, 503)

    def test_google_rtdn_endpoint_delegates_oidc_validation_to_processor(self):
        processor = Mock()
        processor.process.return_value = True
        self.service.google_rtdn_processor = processor
        request = Request(
            self.base_url + "/v1/store/google/rtdn",
            data=b'{"message":{"messageId":"event","data":"e30="}}',
            headers={"Authorization": "Bearer google-oidc-token", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {"status": "processed"})
        processor.process.assert_called_once()

    def test_google_rtdn_endpoint_fails_closed_when_unconfigured(self):
        self.service.google_rtdn_processor = None
        request = Request(
            self.base_url + "/v1/store/google/rtdn",
            data=b'{"message":{"messageId":"event","data":"e30="}}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, 503)

    def test_unconfigured_purchase_verification_fails_closed(self):
        self.service.store_verification_service = None
        request = Request(
            self.base_url + "/v1/store/verify-purchase", data=b'{"provider":"apple"}',
            headers={"Authorization": "Bearer valid-bearer-token"}, method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, 503)

    def test_provider_verification_error_does_not_grant_access(self):
        self.store_verifier.verify_and_persist.side_effect = StoreVerificationError("invalid")
        request = Request(
            self.base_url + "/v1/store/verify-purchase",
            data=json.dumps({
                "provider": "apple", "purchase_token": "bad-jws",
                "product_id": "premium.monthly", "application_id": "com.illumyx.illumyxapp",
            }).encode(),
            headers={"Authorization": "Bearer valid-bearer-token"}, method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, 400)

    def test_expired_or_revoked_session_is_rejected(self):
        self.service.resolve_session.side_effect = AuthenticationError(AuthFailure.REVOKED_SESSION)
        with self.assertRaises(HTTPError) as raised:
            self.request()
        self.assertEqual(raised.exception.code, 401)
        self.binding_service.get_or_create_for_session.assert_not_called()


class FamilyInvitationHttpApiTests(StoreBindingHttpApiTests):
    """HTTP boundary tests for authenticated Family invitation operations."""

    def setUp(self):
        super().setUp()
        self.family_service = Mock()
        self.family_service.create_invitation.return_value = {
            "invitation_id": "invite_1234567890123456",
            "invitation_code": "one-time-secret",
            "expires_at": "2026-11-15T12:00:00+00:00",
        }
        self.family_service.list_invitations.return_value = [
            {"invitation_id": "invite_1234567890123456", "status": "pending"}
        ]
        self.family_service.accept_invitation.return_value = {"joined": True}
        self.family_service.revoke_invitation.return_value = True
        self.service.family_invitation_service = self.family_service

    def family_request(self, path, *, method="POST", token="valid-bearer-token", body=None):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        payload = json.dumps(body or {}).encode() if method in {"POST", "PATCH"} else None
        request = Request(
            self.base_url + path,
            data=payload,
            headers=headers,
            method=method,
        )
        return urlopen(request, timeout=3)

    def test_create_invitation_uses_authenticated_owner_and_returns_one_time_code(self):
        with self.family_request("/v1/family/invitations") as response:
            self.assertEqual(response.status, 201)
            result = json.loads(response.read())
            self.assertEqual(result["invitation_code"], "one-time-secret")
        self.family_service.create_invitation.assert_called_once_with("server-resolved-subject")

    def test_list_invitations_uses_authenticated_owner_identity(self):
        request = Request(
            self.base_url + "/v1/family/invitations",
            headers={"Authorization": "Bearer valid-bearer-token"},
            method="GET",
        )
        with urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["invitations"][0]["status"], "pending")
        self.family_service.list_invitations.assert_called_once_with("server-resolved-subject")

    def test_accept_invitation_uses_authenticated_recipient_not_client_subject(self):
        with self.family_request(
            "/v1/family/invitations/accept",
            body={
                "invitation_code": "recipient-code",
                "subject_id": "attacker-selected-subject",
                "owner_subject_id": "attacker-selected-owner",
            },
        ) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {"joined": True})
        self.family_service.accept_invitation.assert_called_once_with(
            "server-resolved-subject", "recipient-code"
        )

    def test_revoke_invitation_uses_authenticated_owner_identity(self):
        request = Request(
            self.base_url + "/v1/family/invitations/invite_1234567890123456",
            headers={"Authorization": "Bearer valid-bearer-token"},
            method="DELETE",
        )
        with urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {"revoked": True})
        self.family_service.revoke_invitation.assert_called_once_with(
            "server-resolved-subject", "invite_1234567890123456"
        )

    def test_family_routes_reject_missing_bearer_before_service_access(self):
        request = Request(
            self.base_url + "/v1/family/invitations",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, 401)
        self.family_service.create_invitation.assert_not_called()

    def test_family_routes_fail_closed_when_service_is_unconfigured(self):
        self.service.family_invitation_service = None
        with self.assertRaises(HTTPError) as raised:
            self.family_request("/v1/family/invitations")
        self.assertEqual(raised.exception.code, 503)


if __name__ == "__main__":
    unittest.main()
