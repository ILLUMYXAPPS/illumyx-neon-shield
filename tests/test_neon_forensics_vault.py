import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from neon_forensics_vault import EvidenceVault, RetentionPolicy


class EvidenceVaultTests(unittest.TestCase):
    def test_round_trip_is_encrypted_and_recoverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = EvidenceVault(tmp, b"k" * 32)
            path = vault.put(
                "EVD-123", b"sensitive evidence", collected_at_utc="2026-08-26T00:00:00Z",
                classification="CONSENT_REQUIRED", content_type="application/octet-stream",
            )
            self.assertTrue(path.exists())
            self.assertNotIn(b"sensitive evidence", path.read_bytes())
            self.assertEqual(vault.get("EVD-123"), b"sensitive evidence")

    def test_wrong_key_cannot_decrypt(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = EvidenceVault(tmp, b"k" * 32)
            vault.put("EVD-123", b"secret", collected_at_utc="2026-08-26T00:00:00Z",
                      classification="SAFE_TO_COLLECT", content_type="text/plain")
            other = EvidenceVault(tmp, b"x" * 32)
            with self.assertRaises(Exception):
                other.get("EVD-123")

    def test_retention_deletes_expired_standard_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = EvidenceVault(tmp, b"k" * 32, RetentionPolicy(standard_days=30))
            vault.put("EVD-123", b"old", collected_at_utc="2026-07-01T00:00:00Z",
                      classification="SAFE_TO_COLLECT", content_type="text/plain")
            deleted = vault.purge_expired(now=datetime(2026, 8, 26, tzinfo=timezone.utc))
            self.assertEqual(deleted, ["EVD-123.nse"])

    def test_consent_evidence_gets_longer_forensic_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = EvidenceVault(tmp, b"k" * 32, RetentionPolicy(forensic_days=90, standard_days=30))
            vault.put("EVD-123", b"evidence", collected_at_utc="2026-07-15T00:00:00Z",
                      classification="CONSENT_REQUIRED", content_type="text/plain")
            deleted = vault.purge_expired(now=datetime(2026, 8, 26, tzinfo=timezone.utc))
            self.assertEqual(deleted, [])


if __name__ == "__main__":
    unittest.main()
