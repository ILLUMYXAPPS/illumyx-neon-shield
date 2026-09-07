"""Code-reviewed production migration definitions for the auth store."""
from __future__ import annotations

from backend.migrations import Migration


PRODUCTION_MIGRATIONS = (
    Migration(
        1,
        "create_auth_tables",
        (
            "CREATE TABLE IF NOT EXISTS users (subject_id TEXT PRIMARY KEY, identity_hash TEXT UNIQUE NOT NULL, credential_record TEXT NOT NULL, blocked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS devices (subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, trusted INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, PRIMARY KEY(subject_id, device_hash), FOREIGN KEY(subject_id) REFERENCES users(subject_id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS blocked_phones (phone_hash TEXT PRIMARY KEY, created_at TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS sessions (session_hash TEXT PRIMARY KEY, subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, issued_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(subject_id) REFERENCES users(subject_id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS audit_events (event_hash TEXT PRIMARY KEY, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, subject_id TEXT, device_fingerprint TEXT NOT NULL, previous_hash TEXT NOT NULL)",
        ),
    ),
    Migration(
        2,
        "create_auth_indexes",
        (
            "CREATE INDEX IF NOT EXISTS idx_managed_sessions_subject ON sessions(subject_id)",
            "CREATE INDEX IF NOT EXISTS idx_managed_audit_time ON audit_events(occurred_at)",
        ),
    ),
    Migration(
        3,
        "create_sign_in_rate_limits",
        (
            "CREATE TABLE IF NOT EXISTS sign_in_rate_limits (identity_hash TEXT PRIMARY KEY, failure_count INTEGER NOT NULL, window_started_at TEXT NOT NULL)",
        ),
    ),
)
