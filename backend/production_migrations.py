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
        "create_store_subscription_records",
        (
            "CREATE TABLE IF NOT EXISTS verified_subscriptions (subscription_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, provider TEXT NOT NULL CHECK(provider IN ('apple','google_play')), application_id TEXT NOT NULL, product_id TEXT NOT NULL, package TEXT NOT NULL CHECK(package IN ('premium','premium_family')), environment TEXT NOT NULL CHECK(environment IN ('production','sandbox')), account_binding_id TEXT NOT NULL, transaction_id TEXT NOT NULL, original_transaction_id TEXT NOT NULL, purchase_token_hash TEXT NOT NULL, expires_at TEXT, revoked INTEGER NOT NULL DEFAULT 0, verified_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(subject_id) REFERENCES users(subject_id) ON DELETE CASCADE, UNIQUE(provider, original_transaction_id))",
            "CREATE INDEX IF NOT EXISTS idx_verified_subscriptions_subject ON verified_subscriptions(subject_id)",
            "CREATE INDEX IF NOT EXISTS idx_verified_subscriptions_expiry ON verified_subscriptions(expires_at)",
            "CREATE TABLE IF NOT EXISTS store_notification_events (provider TEXT NOT NULL CHECK(provider IN ('apple','google_play')), event_id TEXT NOT NULL, event_type TEXT NOT NULL, payload_hash TEXT NOT NULL, received_at TEXT NOT NULL, processed_at TEXT, processing_status TEXT NOT NULL CHECK(processing_status IN ('received','processed','rejected')), PRIMARY KEY(provider, event_id))",
            "CREATE INDEX IF NOT EXISTS idx_store_notification_status ON store_notification_events(processing_status, received_at)",
        ),
    ),
    Migration(
        5,
        "create_store_account_bindings",
        (
            "CREATE TABLE IF NOT EXISTS store_account_bindings (subject_id TEXT PRIMARY KEY, binding_id TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(subject_id) REFERENCES users(subject_id) ON DELETE CASCADE)",
        ),
    ),
    Migration(
        6,
        "create_family_membership_records",
        (
            "CREATE TABLE IF NOT EXISTS family_households (owner_subject_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, FOREIGN KEY(owner_subject_id) REFERENCES users(subject_id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS family_memberships (owner_subject_id TEXT NOT NULL, member_subject_id TEXT NOT NULL UNIQUE, role TEXT NOT NULL CHECK(role IN ('owner','member')), status TEXT NOT NULL CHECK(status IN ('active','removed')), created_at TEXT NOT NULL, PRIMARY KEY(owner_subject_id,member_subject_id), FOREIGN KEY(owner_subject_id) REFERENCES family_households(owner_subject_id) ON DELETE CASCADE, FOREIGN KEY(member_subject_id) REFERENCES users(subject_id) ON DELETE CASCADE)",
            "CREATE INDEX IF NOT EXISTS idx_family_memberships_owner ON family_memberships(owner_subject_id,status)",
        ),
    ),
    Migration(
        7,
        "create_device_pairing_tables",
        (
            "CREATE TABLE IF NOT EXISTS device_pairing_requests (request_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, device_name TEXT NOT NULL, secret_hash TEXT NOT NULL, code_hash TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, expires_at TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS idx_managed_pairing_subject ON device_pairing_requests(subject_id, status)",
            "CREATE TABLE IF NOT EXISTS device_labels (subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, device_name TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(subject_id, device_hash))",
        ),
    ),
    Migration(
        8,
        "create_family_invitations",
        (
            "CREATE TABLE IF NOT EXISTS family_invitations (invitation_id TEXT PRIMARY KEY, owner_subject_id TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','accepted','revoked','expired')), created_at TEXT NOT NULL, expires_at TEXT NOT NULL, accepted_by TEXT, accepted_at TEXT, FOREIGN KEY(owner_subject_id) REFERENCES users(subject_id) ON DELETE CASCADE, FOREIGN KEY(accepted_by) REFERENCES users(subject_id) ON DELETE SET NULL)",
            "CREATE INDEX IF NOT EXISTS idx_family_invitations_owner_status ON family_invitations(owner_subject_id,status,expires_at)",
        ),
    ),
    Migration(
        9,
        "create_serialized_audit_chain_head",
        (
            "CREATE TABLE IF NOT EXISTS audit_chain_head (chain_id INTEGER PRIMARY KEY CHECK(chain_id=1), event_hash TEXT NOT NULL)",
            "INSERT INTO audit_chain_head(chain_id,event_hash) SELECT 1, COALESCE((SELECT event_hash FROM audit_events ORDER BY occurred_at DESC,event_hash DESC LIMIT 1), '0000000000000000000000000000000000000000000000000000000000000000') WHERE NOT EXISTS (SELECT 1 FROM audit_chain_head WHERE chain_id=1)",
        ),
    ),
)
