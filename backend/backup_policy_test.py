import unittest

from backend.backup_policy import (
    BackupPolicy,
    BackupRecord,
    RestoreVerification,
    validate_backup_record,
    validate_restore_verification,
)


class BackupPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = BackupPolicy()

    def test_default_policy_requires_encryption_and_restore_testing(self):
        self.assertEqual(self.policy.rpo_minutes, 15)
        self.assertEqual(self.policy.rto_minutes, 60)
        self.assertEqual(self.policy.retention_days, 35)
        self.assertTrue(self.policy.encryption_required)
        self.assertTrue(self.policy.restore_test_required)

    def test_policy_rejects_unsafe_values(self):
        with self.assertRaises(ValueError):
            BackupPolicy(rpo_minutes=0)
        with self.assertRaises(ValueError):
            BackupPolicy(rto_minutes=0)
        with self.assertRaises(ValueError):
            BackupPolicy(retention_days=0)
        with self.assertRaises(ValueError):
            BackupPolicy(encryption_required=False)
        with self.assertRaises(ValueError):
            BackupPolicy(restore_test_required=False)

    def test_backup_requires_encryption_integrity_and_remote_storage(self):
        valid = BackupRecord(
            "backup-001",
            "2026-09-07T01:00:00+00:00",
            True,
            True,
            "s3://neon-shield-backups/prod/backup-001",
        )
        validate_backup_record(valid, self.policy)

        with self.assertRaises(RuntimeError):
            validate_backup_record(
                BackupRecord(valid.backup_id, valid.completed_at, False, True, valid.storage_uri),
                self.policy,
            )
        with self.assertRaises(RuntimeError):
            validate_backup_record(
                BackupRecord(valid.backup_id, valid.completed_at, True, False, valid.storage_uri),
                self.policy,
            )
        with self.assertRaises(ValueError):
            validate_backup_record(
                BackupRecord(valid.backup_id, valid.completed_at, True, True, "file:///backup"),
                self.policy,
            )

    def test_backup_timestamp_must_be_explicit_utc(self):
        record = BackupRecord(
            "backup-001",
            "2026-09-07T01:00:00",
            True,
            True,
            "https://backup.example/backup-001",
        )
        with self.assertRaises(ValueError):
            validate_backup_record(record, self.policy)

    def test_restore_verification_requires_both_check_classes(self):
        valid = RestoreVerification(
            "backup-001",
            "2026-09-07T02:00:00+00:00",
            7,
            True,
            True,
        )
        validate_restore_verification(valid, self.policy)

        with self.assertRaises(RuntimeError):
            validate_restore_verification(
                RestoreVerification(valid.backup_id, valid.verified_at, 7, False, True),
                self.policy,
            )
        with self.assertRaises(RuntimeError):
            validate_restore_verification(
                RestoreVerification(valid.backup_id, valid.verified_at, 7, True, False),
                self.policy,
            )

    def test_restore_verification_rejects_invalid_schema_or_timestamp(self):
        with self.assertRaises(ValueError):
            validate_restore_verification(
                RestoreVerification("backup-001", "2026-09-07T02:00:00+00:00", 0, True, True),
                self.policy,
            )
        with self.assertRaises(ValueError):
            validate_restore_verification(
                RestoreVerification("backup-001", "2026-09-07T02:00:00", 7, True, True),
                self.policy,
            )


if __name__ == "__main__":
    unittest.main()
