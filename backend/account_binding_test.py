"""Tests for server-issued account-to-store binding persistence."""
from __future__ import annotations
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from auth_server import AuthenticationError, InMemoryIdentityService
from auth_server_contract import SignInRequest
from backend.account_binding import AccountBindingRepository, AuthenticatedStoreAccountBindingService
from backend.migrations import MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS

class AccountBindingRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "bindings.sqlite3"
        def connect():
            connection = sqlite3.connect(path)
            connection.execute("PRAGMA foreign_keys=ON")
            return connection
        self.connect = connect
        MigrationRunner(connect, PRODUCTION_MIGRATIONS).apply_pending()
        with connect() as connection:
            connection.execute(
                "INSERT INTO users(subject_id,identity_hash,credential_record,created_at) VALUES(?,?,?,?)",
                ("subject-1", "identity-1", "credential", "2026-11-07T00:00:00+00:00"),
            )
        self.repository = AccountBindingRepository(connect, placeholder="?")

    def test_binding_is_stable_for_same_authenticated_subject(self):
        first = self.repository.get_or_create(authenticated_subject_id="subject-1")
        second = self.repository.get_or_create(authenticated_subject_id="subject-1")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 36)

    def test_binding_is_unique_per_account(self):
        first = self.repository.get_or_create(authenticated_subject_id="subject-1")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO users(subject_id,identity_hash,credential_record,created_at) VALUES(?,?,?,?)",
                ("subject-2", "identity-2", "credential", "2026-11-07T00:00:00+00:00"),
            )
        second = self.repository.get_or_create(authenticated_subject_id="subject-2")
        self.assertNotEqual(first, second)

    def test_verified_store_binding_resolves_to_subject(self):
        binding = self.repository.get_or_create(authenticated_subject_id="subject-1")
        self.assertEqual(self.repository.get_subject_for_binding(binding), "subject-1")
        self.assertIsNone(self.repository.get_subject_for_binding("unknown-binding"))

    def test_unknown_subject_cannot_receive_binding(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.get_or_create(authenticated_subject_id="invented-subject")

    def test_invalid_subject_is_rejected(self):
        for value in ("", "   ", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.repository.get_or_create(authenticated_subject_id=value)

if __name__ == "__main__":
    unittest.main()

class AuthenticatedBindingServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "authenticated-bindings.sqlite3"
        def connect():
            connection = sqlite3.connect(path)
            connection.execute("PRAGMA foreign_keys=ON")
            return connection
        self.connect = connect
        MigrationRunner(connect, PRODUCTION_MIGRATIONS).apply_pending()
        with connect() as connection:
            connection.execute(
                "INSERT INTO users(subject_id,identity_hash,credential_record,created_at) VALUES(?,?,?,?)",
                ("subject-auth", "identity-auth", "credential", "2026-11-07T00:00:00+00:00"),
            )
        self.identity = InMemoryIdentityService(
            verify_credential=lambda identity, credential: (
                "subject-auth" if identity == "owner@example.test" and credential == "correct" else None
            ),
            trusted_devices={"trusted-device"},
        )
        self.repository = AccountBindingRepository(connect, placeholder="?")
        self.service = AuthenticatedStoreAccountBindingService(self.identity, self.repository)

    def _session(self):
        return self.identity.sign_in(
            SignInRequest("owner@example.test", "correct", "trusted-device")
        )

    def test_binding_is_issued_from_resolved_session(self):
        session = self._session()
        binding = self.service.get_or_create_for_session(session_id=session.session_id)
        self.assertEqual(binding, self.service.get_or_create_for_session(session_id=session.session_id))

    def test_invalid_or_revoked_session_cannot_obtain_binding(self):
        with self.assertRaises(AuthenticationError):
            self.service.get_or_create_for_session(session_id="not-a-session")
        session = self._session()
        self.identity.revoke(session)
        with self.assertRaises(AuthenticationError):
            self.service.get_or_create_for_session(session_id=session.session_id)

    def test_untrusted_device_session_cannot_obtain_binding(self):
        session = self._session()
        self.identity._trusted_devices.remove("trusted-device")
        with self.assertRaises(AuthenticationError):
            self.service.get_or_create_for_session(session_id=session.session_id)

