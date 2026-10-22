import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from security_checks import CheckResult
from smart_scan_scheduler import (
    APP_IDLE_SECONDS,
    INTERVAL_SECONDS,
    SmartScanStore,
    build_evidence_record,
)


class SmartScanEvidenceTests(unittest.TestCase):
    def test_verified_clear_record_contains_only_timestamp_and_status(self):
        result = build_evidence_record(
            [CheckResult("Firewall", "Enabled", "ok", "Should not be retained")],
            "2026-10-22T08:00:00+10:00",
        )
        self.assertEqual(result, {
            "timestamp": "2026-10-22T08:00:00+10:00",
            "status": "verified_clear",
        })
        self.assertNotIn("issues", result)

    def test_non_clear_record_keeps_relevant_issue_and_timestamp(self):
        result = build_evidence_record(
            [CheckResult("Firewall", "Disabled", "warn", "Needs review")],
            "2026-10-22T08:00:00+10:00",
        )
        self.assertEqual(result["status"], "issue_or_uncertain")
        self.assertEqual(result["timestamp"], "2026-10-22T08:00:00+10:00")
        self.assertEqual(result["issues"][0]["check"], "Firewall")
        self.assertEqual(result["issues"][0]["detail"], "Needs review")

    def test_empty_results_are_uncertain_not_clear(self):
        result = build_evidence_record([], "2026-10-22T08:00:00+10:00")
        self.assertEqual(result["status"], "issue_or_uncertain")
        self.assertEqual(result["issues"][0]["state"], "uncertain")

    def test_informational_result_is_not_mislabelled_clear(self):
        result = build_evidence_record([CheckResult("Firewall", "Unknown", "info", "Unavailable")])
        self.assertEqual(result["status"], "issue_or_uncertain")


class SmartScanStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = SmartScanStore(Path(self.temp.name) / "smart_scan.json")

    def tearDown(self):
        self.temp.cleanup()

    def test_initial_schedule_is_one_hour_from_now(self):
        now = datetime.fromisoformat("2026-10-22T08:00:00+10:00")
        self.store.initialise_schedule(now)
        self.assertEqual(
            datetime.fromisoformat(self.store.data["next_due_at"]),
            now + timedelta(seconds=INTERVAL_SECONDS),
        )

    def test_due_schedule_is_detected(self):
        now = datetime.fromisoformat("2026-10-22T08:00:00+10:00")
        self.store.data["next_due_at"] = (now - timedelta(seconds=1)).isoformat()
        self.assertTrue(self.store.is_due(now))

    def test_paused_schedule_is_not_due(self):
        now = datetime.fromisoformat("2026-10-22T08:00:00+10:00")
        self.store.data["enabled"] = False
        self.store.data["next_due_at"] = (now - timedelta(seconds=1)).isoformat()
        self.assertFalse(self.store.is_due(now))

    def test_completion_persists_policy_limited_evidence_and_next_due(self):
        now = datetime.fromisoformat("2026-10-22T08:00:00+10:00")
        self.store.complete_scan([CheckResult("Firewall", "Enabled", "ok", "Private detail")], now)
        reopened = SmartScanStore(self.store.path)
        self.assertEqual(reopened.data["history"][-1], {
            "timestamp": "2026-10-22T08:00:00+10:00",
            "status": "verified_clear",
        })
        self.assertEqual(datetime.fromisoformat(reopened.data["next_due_at"]), now + timedelta(seconds=INTERVAL_SECONDS))

    def test_evidence_history_is_capped(self):
        for _ in range(105):
            self.store.complete_scan([CheckResult("Firewall", "Enabled", "ok")])
        self.assertEqual(len(self.store.data["history"]), 100)

    def test_idle_preference_uses_five_minute_app_idle_threshold(self):
        self.assertEqual(APP_IDLE_SECONDS, 300)


if __name__ == "__main__":
    unittest.main()
