"""Tests for durable verified subscription and notification persistence."""
from __future__ import annotations

import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.migrations import MigrationRunner
from backend.production_migrations import PRODUCTION_MIGRATIONS
from backend.subscription_store import StoreSubscriptionRepository, SubscriptionPersistenceError
from entitlements import Package
from store_verification import StoreProvider, StorePurchaseRequest, VerifiedStorePurchase


NOW = datetime(2026, 11, 7, 10, 0, tzinfo=timezone.utc)


class StoreSubscriptionRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "subscriptions.sqlite3"

        def connect():
            connection = sqlite3.connect(self.path)
            connection.execute("PRAGMA foreign_keys=ON")
            return connection

        self.connect = connect
        MigrationRunner(self.connect, PRODUCTION_MIGRATIONS).apply_pending()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO users(subject_id,identity_hash,credential_record,created_at) VALUES(?,?,?,?)",
                ("subject-1", "identity-hash", "credential", NOW.isoformat()),
            )
        self.repository = StoreSubscriptionRepository(self.connect, pepper="test-pepper", placeholder="?")
        self.request = StorePurchaseRequest(
            StoreProvider.APPLE, "sensitive-purchase-token", "premium.monthly",
            "com.illumyx.illumyxapp", "account-binding-1",
        )
        self.purchase = VerifiedStorePurchase(
            StoreProvider.APPLE, "premium.monthly", "com.illumyx.illumyxapp",
            "account-binding-1", "transaction-1", "original-transaction-1",
            NOW + timedelta(days=30), environment="production",
        )

    def save(self, subject="subject-1", purchase=None):
        self.repository.save_verified_purchase(
            subject_id=subject, request=self.request, purchase=purchase or self.purchase,
            package=Package.PREMIUM, verified_at=NOW,
        )

    def test_persists_verified_purchase_and_returns_paid_snapshot(self):
        self.save()
        snapshot = self.repository.get_subscription_snapshot("subject-1", now=NOW)
        self.assertIs(snapshot.package, Package.PREMIUM)
        self.assertTrue(snapshot.is_current(NOW))

    def test_raw_purchase_token_is_not_stored(self):
        self.save()
        with self.connect() as connection:
            stored = connection.execute(
                "SELECT purchase_token_hash FROM verified_subscriptions"
            ).fetchone()[0]
        self.assertNotEqual(stored, self.request.purchase_token)
        self.assertEqual(len(stored), 64)

    def test_transaction_cannot_be_reassigned_to_another_account(self):
        self.save()
        with self.assertRaises(SubscriptionPersistenceError):
            self.save(subject="attacker-subject")

    def test_expired_or_revoked_subscription_falls_back_to_free(self):
        expired = VerifiedStorePurchase(
            StoreProvider.APPLE, "premium.monthly", "com.illumyx.illumyxapp",
            "account-binding-1", "transaction-2", "original-transaction-2",
            NOW - timedelta(seconds=1),
        )
        self.save(purchase=expired)
        self.assertIs(
            self.repository.get_subscription_snapshot("subject-1", now=NOW).package,
            Package.FREE,
        )

    def test_notification_is_idempotent_and_finalized_once(self):
        args = dict(provider=StoreProvider.GOOGLE_PLAY, event_id="event-1",
                    event_type="subscription.updated", payload=b"authenticated-payload", received_at=NOW)
        self.assertTrue(self.repository.record_notification(**args))
        self.assertFalse(self.repository.record_notification(**args))
        self.assertTrue(self.repository.finish_notification(
            provider=StoreProvider.GOOGLE_PLAY, event_id="event-1", processed=True, processed_at=NOW))
        self.assertFalse(self.repository.finish_notification(
            provider=StoreProvider.GOOGLE_PLAY, event_id="event-1", processed=False, processed_at=NOW))
        with self.connect() as connection:
            row = connection.execute(
                "SELECT processing_status FROM store_notification_events WHERE event_id='event-1'"
            ).fetchone()
        self.assertEqual(row[0], "processed")

    def test_unconfigured_or_unknown_account_has_no_paid_entitlement(self):
        self.assertIs(
            self.repository.get_subscription_snapshot("subject-1", now=NOW).package,
            Package.FREE,
        )


if __name__ == "__main__":
    unittest.main()
