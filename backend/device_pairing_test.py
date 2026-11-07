"""Security and lifecycle tests for universal device pairing."""
from __future__ import annotations

import unittest
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
import sqlite3
import tempfile
from pathlib import Path

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, SignInRequest
from backend.managed_db_store import ManagedDbAuthStore
from backend.service import PersistentIdentityService
from backend.store import AuthStore
from backend.device_limits import DeviceAllowance, DevicePackage, DeviceLimitExceeded
from backend.http_api import make_handler


class DevicePairingTests(unittest.TestCase):
    def setUp(self):
        self.store = AuthStore(':memory:', pepper='pairing-test-pepper')
        self.store.create_user('subject-a', 'owner@example.test', 'correct-password')
        self.store.trust_device('subject-a', 'existing-device')
        self.service = PersistentIdentityService(self.store)
        self.existing_session = self.service.sign_in(SignInRequest('owner@example.test', 'correct-password', 'existing-device'))
        self.pairing = self.service.device_pairing

    def tearDown(self):
        self.store.close()

    def test_pair_approve_sign_in_rename_and_unlink(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'new-device', 'My iPad')
        self.assertEqual(self.pairing.status(started['request_id'], started['pairing_secret']), 'pending')
        approved = self.pairing.approve(self.existing_session, started['request_id'], pairing_code=started['pairing_code'])
        self.assertEqual(approved['status'], 'approved')
        self.assertEqual(self.pairing.status(started['request_id'], started['pairing_secret']), 'approved')
        new_session = self.service.sign_in(SignInRequest('owner@example.test', 'correct-password', 'new-device'))
        devices = self.pairing.devices(self.existing_session)
        new_device = next(item for item in devices if item['device_name'] == 'My iPad')
        self.pairing.rename(self.existing_session, new_device['device_ref'], 'ILLUMYX iPad')
        self.assertIn('ILLUMYX iPad', [item['device_name'] for item in self.pairing.devices(self.existing_session)])
        self.pairing.unlink(self.existing_session, new_device['device_ref'])
        with self.assertRaises(AuthenticationError) as caught:
            self.service.resolve_session(new_session.session_id)
        self.assertEqual(caught.exception.failure, AuthFailure.UNTRUSTED_DEVICE)
        with self.assertRaises(AuthenticationError) as sign_in_error:
            self.service.sign_in(SignInRequest('owner@example.test', 'correct-password', 'new-device'))
        self.assertEqual(sign_in_error.exception.failure, AuthFailure.UNTRUSTED_DEVICE)

    def test_verified_premium_allowance_blocks_fourth_device_before_trust(self):
        self.pairing.allowance_resolver = lambda subject_id, request_id: DeviceAllowance(
            DevicePackage.PREMIUM, 3
        )
        started = self.pairing.start(
            'owner@example.test', 'correct-password', 'fourth-device', 'Fourth device'
        )
        with self.assertRaises(DeviceLimitExceeded):
            self.pairing.approve(
                self.existing_session, started['request_id'],
                pairing_code=started['pairing_code'],
            )
        self.assertFalse(self.store.device_trusted('subject-a', 'fourth-device'))
        self.assertEqual(
            self.pairing.status(started['request_id'], started['pairing_secret']),
            'pending',
        )

    def test_pairing_secret_is_not_stored_in_plaintext_and_code_is_hashed(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'new-device', 'Android phone')
        row = self.store._db.execute('SELECT secret_hash, code_hash FROM device_pairing_requests WHERE request_id=?', (started['request_id'],)).fetchone()
        self.assertNotEqual(row['secret_hash'], started['pairing_secret'])
        self.assertNotEqual(row['code_hash'], started['pairing_code'])

    def test_wrong_code_consumes_attempt_and_replay_is_rejected(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'another-device', 'Laptop')
        with self.assertRaises(AuthenticationError):
            self.pairing.approve(self.existing_session, started['request_id'], pairing_code='000000' if started['pairing_code'] != '000000' else '000001')
        self.pairing.approve(self.existing_session, started['request_id'], pairing_code=started['pairing_code'])
        with self.assertRaises(AuthenticationError):
            self.pairing.approve(self.existing_session, started['request_id'], pairing_code=started['pairing_code'])

    def test_other_account_cannot_approve_request(self):
        self.store.create_user('subject-b', 'other@example.test', 'other-password')
        self.store.trust_device('subject-b', 'other-device')
        other = self.service.sign_in(SignInRequest('other@example.test', 'other-password', 'other-device'))
        started = self.pairing.start('owner@example.test', 'correct-password', 'target-device', 'Tablet')
        with self.assertRaises(AuthenticationError):
            self.pairing.approve(other, started['request_id'], pairing_code=started['pairing_code'])
        self.assertFalse(self.store.device_trusted('subject-b', 'target-device'))

    def test_five_failed_codes_lock_out_the_correct_code(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'locked-device', 'Laptop')
        wrong_code = '000000' if started['pairing_code'] != '000000' else '000001'
        for _ in range(5):
            with self.assertRaises(AuthenticationError):
                self.pairing.approve(self.existing_session, started['request_id'], pairing_code=wrong_code)
        with self.assertRaises(AuthenticationError) as caught:
            self.pairing.approve(self.existing_session, started['request_id'], pairing_code=started['pairing_code'])
        self.assertEqual(caught.exception.failure, AuthFailure.RATE_LIMITED)
        self.assertFalse(self.store.device_trusted('subject-a', 'locked-device'))

    def test_status_polling_is_rate_limited_per_pairing_request(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'poll-device', 'Tablet')
        for _ in range(self.pairing.MAX_STATUS_POLLS_PER_WINDOW):
            self.assertEqual(
                self.pairing.status(started['request_id'], started['pairing_secret']),
                'pending',
            )
        with self.assertRaises(AuthenticationError) as caught:
            self.pairing.status(started['request_id'], started['pairing_secret'])
        self.assertEqual(caught.exception.failure, AuthFailure.RATE_LIMITED)

    def test_invalid_polling_secret_does_not_consume_poll_allowance(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'poll-secret-device', 'Phone')
        with self.assertRaises(AuthenticationError):
            self.pairing.status(started['request_id'], 'incorrect-secret')
        self.assertEqual(
            self.pairing.status(started['request_id'], started['pairing_secret']),
            'pending',
        )

    def test_expired_pairing_request_cannot_be_approved(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'expired-device', 'Tablet')
        expired_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.store._db.execute(
            'UPDATE device_pairing_requests SET expires_at=? WHERE request_id=?',
            (expired_at, started['request_id']),
        )
        self.store._db.commit()
        self.assertEqual(self.pairing.status(started['request_id'], started['pairing_secret']), 'expired')
        with self.assertRaises(AuthenticationError):
            self.pairing.approve(self.existing_session, started['request_id'], pairing_code=started['pairing_code'])
        self.assertFalse(self.store.device_trusted('subject-a', 'expired-device'))

    def test_http_pairing_endpoint_uses_only_six_digit_code(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.service))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_address[1]}'

        def post(path, payload, token=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = f'Bearer {token}'
            request = Request(
                base + path,
                data=json.dumps(payload).encode(),
                headers=headers,
                method='POST',
            )
            with urlopen(request, timeout=3) as response:
                body = response.read()
                return response.status, json.loads(body) if body else {}

        try:
            status, started = post('/v1/device-pairing/start', {
                'identity': 'owner@example.test',
                'credential': 'correct-password',
                'device_id': 'http-new-device',
                'device_name': 'HTTP test device',
            })
            self.assertEqual(status, 201)
            self.assertNotIn('qr_payload', started)
            self.assertIn('pairing_code', started)
            self.assertIn('pairing_secret', started)

            status, approved = post('/v1/device-pairing/approve', {
                'request_id': started['request_id'],
                'pairing_code': started['pairing_code'],
            }, self.existing_session.session_id)
            self.assertEqual(status, 200)
            self.assertEqual(approved['status'], 'approved')
            self.assertTrue(self.store.device_trusted('subject-a', 'http-new-device'))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_current_device_cannot_unlink_itself(self):
        own_ref = self.pairing.devices(self.existing_session)[0]['device_ref']
        with self.assertRaises(ValueError):
            self.pairing.unlink(self.existing_session, own_ref)

    def test_managed_database_adapter_supports_pairing_after_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'managed-pairing.sqlite3'
            store = ManagedDbAuthStore(
                lambda: sqlite3.connect(database_path),
                pepper='managed-pairing-pepper',
                placeholder='?',
                audit_lock_clause='',
            )
            store.migrate()
            store.create_user('managed-subject', 'managed@example.test', 'managed-password')
            store.trust_device('managed-subject', 'managed-existing')
            service = PersistentIdentityService(store)
            trusted = service.sign_in(SignInRequest(
                'managed@example.test', 'managed-password', 'managed-existing'
            ))
            request = service.device_pairing.start(
                'managed@example.test', 'managed-password', 'managed-new', 'Managed tablet'
            )
            service.device_pairing.approve(
                trusted, request['request_id'], pairing_code=request['pairing_code']
            )
            self.assertTrue(store.device_trusted('managed-subject', 'managed-new'))


if __name__ == '__main__':
    unittest.main()