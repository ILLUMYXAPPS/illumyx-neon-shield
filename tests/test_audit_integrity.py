import hashlib
import sqlite3
import unittest

from backend.audit_integrity import GENESIS_HASH, verify_audit_chain


def make_record(event_type, occurred_at, subject_id, device_fingerprint, previous_hash):
    payload = (
        f"{event_type}|{occurred_at}|{subject_id or ''}|"
        f"{device_fingerprint}|{previous_hash}"
    )
    return {
        "event_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "event_type": event_type,
        "occurred_at": occurred_at,
        "subject_id": subject_id,
        "device_fingerprint": device_fingerprint,
        "previous_hash": previous_hash,
    }


class AuditIntegrityTests(unittest.TestCase):
    def test_empty_chain_is_valid(self):
        result = verify_audit_chain([])
        self.assertTrue(result.valid)
        self.assertEqual(result.event_count, 0)

    def test_valid_chain_passes(self):
        first = make_record("session_issued", "2026-10-11T00:00:00+00:00", "user-1", "device-hash", GENESIS_HASH)
        second = make_record("session_revoked", "2026-10-11T00:01:00+00:00", "user-1", "device-hash", first["event_hash"])
        result = verify_audit_chain([first, second])
        self.assertTrue(result.valid)
        self.assertEqual(result.event_count, 2)

    def test_sqlite_row_records_are_supported(self):
        record = make_record("session_issued", "2026-10-11T00:00:00+00:00", None, "device-hash", GENESIS_HASH)
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.execute(
            "CREATE TABLE audit_events (event_hash TEXT, event_type TEXT, occurred_at TEXT, "
            "subject_id TEXT, device_fingerprint TEXT, previous_hash TEXT)"
        )
        db.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)",
            tuple(record[field] for field in (
                "event_hash", "event_type", "occurred_at", "subject_id",
                "device_fingerprint", "previous_hash"
            )),
        )
        rows = db.execute("SELECT * FROM audit_events ORDER BY rowid").fetchall()
        result = verify_audit_chain(rows)
        db.close()
        self.assertTrue(result.valid)
        self.assertEqual(result.event_count, 1)

    def test_changed_event_content_fails(self):
        record = make_record("session_issued", "2026-10-11T00:00:00+00:00", "user-1", "device-hash", GENESIS_HASH)
        record["event_type"] = "session_revoked"
        result = verify_audit_chain([record])
        self.assertFalse(result.valid)
        self.assertEqual(result.invalid_index, 0)
        self.assertEqual(result.reason, "event_hash_mismatch")

    def test_broken_link_fails(self):
        first = make_record("session_issued", "2026-10-11T00:00:00+00:00", "user-1", "device-hash", GENESIS_HASH)
        second = make_record("session_revoked", "2026-10-11T00:01:00+00:00", "user-1", "device-hash", "f" * 64)
        result = verify_audit_chain([first, second])
        self.assertFalse(result.valid)
        self.assertEqual(result.invalid_index, 1)
        self.assertEqual(result.reason, "chain_link_mismatch")

    def test_missing_field_fails_closed(self):
        record = make_record("session_issued", "2026-10-11T00:00:00+00:00", None, "device-hash", GENESIS_HASH)
        del record["device_fingerprint"]
        result = verify_audit_chain([record])
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "missing_field")

    def test_malformed_hash_fails_closed(self):
        record = make_record("session_issued", "2026-10-11T00:00:00+00:00", None, "device-hash", GENESIS_HASH)
        record["event_hash"] = "not-a-hash"
        result = verify_audit_chain([record])
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "malformed_event_hash")

    def test_non_mapping_record_fails_closed(self):
        result = verify_audit_chain([None])
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "malformed_record")


if __name__ == "__main__":
    unittest.main()
