"""Focused regression tests for the DB-API managed auth adapter."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from backend.managed_db_store import ManagedDbAuthStore
from backend.managed_store import ManagedAuthStore


def _store(tmp: Path) -> ManagedDbAuthStore:
    path = tmp / "managed-test.sqlite3"
    return ManagedDbAuthStore(lambda: sqlite3.connect(path), pepper="test-pepper", placeholder="?")


def test_managed_db_store_implements_contract() -> None:
    with TemporaryDirectory() as directory:
        store = _store(Path(directory))
        assert isinstance(store, ManagedAuthStore)
        store.migrate()


def test_managed_db_store_persists_auth_state() -> None:
    with TemporaryDirectory() as directory:
        store = _store(Path(directory))
        store.migrate()
        store.create_user("subject-1", "User@example.com", "correct horse battery staple")
        store.trust_device("subject-1", "device-1")
        store.block_phone("+61000000000")
        issued = datetime.now(timezone.utc).isoformat()
        expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        store.save_session("opaque-token", "subject-1", "device-1", issued, expires)

        user = store.find_user("user@EXAMPLE.com")
        session = store.get_session("opaque-token")

        assert user is not None
        assert user["subject_id"] == "subject-1"
        assert store.device_trusted("subject-1", "device-1")
        assert store.phone_blocked("+61000000000")
        assert session is not None
        assert session["subject_id"] == "subject-1"
        assert not session["revoked"]

        store.revoke_session("opaque-token")
        assert store.get_session("opaque-token")["revoked"]


def test_managed_db_store_audit_chain_is_linked() -> None:
    with TemporaryDirectory() as directory:
        store = _store(Path(directory))
        store.migrate()
        first = store.add_audit_fingerprint("sign_in", "subject-1", "device-hash-1")
        second = store.add_audit_fingerprint("refresh", "subject-1", "device-hash-1")
        assert first != second
        assert store.last_audit_hash() == second


def test_managed_db_store_requires_pepper() -> None:
    with pytest.raises(RuntimeError, match="pepper"):
        ManagedDbAuthStore(lambda: sqlite3.connect(":memory:"), pepper="", placeholder="?")
