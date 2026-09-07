"""Verify the development SQLite adapter conforms to the managed store contract."""
from __future__ import annotations

from backend.managed_store import ManagedAuthStore
from backend.store import AuthStore


def test_sqlite_auth_store_conforms_to_managed_store_contract() -> None:
    store = AuthStore(":memory:")
    try:
        assert isinstance(store, ManagedAuthStore)
    finally:
        store.close()
