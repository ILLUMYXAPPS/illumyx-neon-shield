"""Security and lifecycle tests for universal device pairing."""
from __future__ import annotations

import unittest
import sqlite3
import tempfile
from pathlib import Path

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure, SignInRequest
from backend.managed_db_store import ManagedDbAuthStore
from backend.service import PersistentIdentityService
from backend.store import AuthStore


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

    def test_pairing_secret_is_not_stored_in_plaintext_and_qr_approval_works(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'qr-device', 'Android phone')
        row = self.store._db.execute('SELECT secret_hash, code_hash FROM device_pairing_requests WHERE request_id=?', (started['request_id'],)).fetchone()
        self.assertNotEqual(row['secret_hash'], started['pairing_secret'])
        self.assertNotEqual(row['code_hash'], started['pairing_code'])
        self.pairing.approve(self.existing_session, started['request_id'], pairing_secret=started['pairing_secret'])
        self.assertTrue(self.store.device_trusted('subject-a', 'qr-device'))

    def test_wrong_code_consumes_attempt_and_replay_is_rejected(self):
        started = self.pairing.start('owner@example.test', 'correct-password', 'another-device', 'Laptop')
        with self.assertRaises(AuthenticationError):
            self.pairing.approve(self.existing_session, started['request_id'], pairing_code='000000' if started['pairing_code'] != '000000' else '000001')
        self.pairing.approve(self.existing_session, started['request_id'], pairing_secret=started['pairing_secret'])
        with self.assertRaises(AuthenticationError):
            self.pairing.approve(self.existing_session, started['request_id'], pairing_secret=started['pairing_secret'])

    def test_other_account_cannot_approve_request(self):
        self.store.create_user('subject-b', 'other@example.test', 'other-password')
        self.store.trust_device('subject-b', 'other-device')
        other = self.service.sign_in(SignInRequest('other@example.test', 'other-password', 'other-device'))
        started = self.pairing.start('owner@example.test', 'correct-password', 'target-device', 'Tablet')
        with self.assertRaises(AuthenticationError):
            self.pairing.approve(other, started['request_id'], pairing_secret=started['pairing_secret'])
        self.assertFalse(self.store.device_trusted('subject-b', 'target-device'))

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