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
    Migration(
        4,
        "create_serialized_audit_chain_head",
        (
            "CREATE TABLE IF NOT EXISTS audit_chain_head (chain_id INTEGER PRIMARY KEY CHECK (chain_id = 1), last_event_hash TEXT NOT NULL)",
            "INSERT INTO audit_chain_head (chain_id, last_event_hash) "
            "SELECT 1, CASE WHEN NOT EXISTS (SELECT 1 FROM audit_events) THEN '" + "0" * 64 + "' "
            "ELSE (SELECT e.event_hash FROM audit_events e WHERE NOT EXISTS "
            "(SELECT 1 FROM audit_events child WHERE child.previous_hash=e.event_hash) LIMIT 1) END "
            "WHERE NOT EXISTS (SELECT 1 FROM audit_events) OR "
            "(SELECT COUNT(*) FROM audit_events e WHERE NOT EXISTS "
            "(SELECT 1 FROM audit_events child WHERE child.previous_hash=e.event_hash)) = 1 "
            "ON CONFLICT (chain_id) DO NOTHING",
        ),
    ),
)
