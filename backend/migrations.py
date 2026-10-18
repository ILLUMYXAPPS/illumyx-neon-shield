"""Explicit, versioned database migration runner for production deployments.

The runner is deliberately separate from application startup. Production
releases invoke it as a deployment step against the managed database.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]
    validate_after_first_statement: Callable[[object], None] | None = None


class MigrationRunner:
    """Apply a validated, contiguous migration set to one DB-API connection."""

    def __init__(
        self,
        connection_factory,
        migrations: tuple[Migration, ...],
        *,
        placeholder: str = "?",
        lock_statement: str | None = None,
    ) -> None:
        if placeholder not in {"%s", "?", ":1"}:
            raise ValueError("unsupported DB-API placeholder")
        self._connection_factory = connection_factory
        self._migrations = self._validate_migrations(migrations)
        self._placeholder = placeholder
        if lock_statement is not None and not lock_statement.startswith("SELECT pg_advisory_xact_lock("):
            raise ValueError("unsupported migration lock statement")
        self._lock_statement = lock_statement

    @staticmethod
    def _validate_migrations(migrations: tuple[Migration, ...]) -> tuple[Migration, ...]:
        ordered = tuple(sorted(migrations, key=lambda migration: migration.version))
        if any(migration.version < 1 for migration in ordered):
            raise ValueError("migration versions must start at 1")
        versions = [migration.version for migration in ordered]
        if len(versions) != len(set(versions)):
            raise ValueError("migration versions must be unique")
        if versions and versions != list(range(1, len(versions) + 1)):
            raise ValueError("migration versions must be contiguous")
        if any(not migration.name.strip() for migration in ordered):
            raise ValueError("migration names must be non-empty")
        if any(not migration.statements for migration in ordered):
            raise ValueError("migrations must contain at least one statement")
        return ordered

    @staticmethod
    def _create_metadata_table(cursor) -> None:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS neon_schema_migrations ("
            "version INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL, "
            "applied_at TEXT NOT NULL)"
        )

    def _insert_applied(self, cursor, migration: Migration) -> None:
        p = self._placeholder
        cursor.execute(
            "INSERT INTO neon_schema_migrations (version, name, applied_at) "
            f"VALUES ({p}, {p}, {p})",
            (migration.version, migration.name, datetime.now(timezone.utc).isoformat()),
        )

    def current_version(self) -> int:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            self._create_metadata_table(cursor)
            connection.commit()
            cursor.execute("SELECT COALESCE(MAX(version), 0) FROM neon_schema_migrations")
            return int(cursor.fetchone()[0])
        except Exception:
            rollback = getattr(connection, "rollback", None)
            if rollback is not None:
                rollback()
            raise
        finally:
            close_cursor = getattr(cursor, "close", None)
            if close_cursor is not None:
                close_cursor()
            connection.close()

    def apply_pending(self) -> int:
        """Apply pending migrations atomically, serializing PostgreSQL deployers."""
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            # Begin before creating metadata or changing schema. SQLite requires
            # an explicit transaction for DDL rollback; IMMEDIATE also serializes
            # competing local migration writers before they inspect history.
            is_sqlite = connection.__class__.__module__.split(".")[0] == "sqlite3"
            cursor.execute("BEGIN IMMEDIATE" if is_sqlite else "BEGIN")

            # PostgreSQL transaction-scoped advisory lock must be acquired before
            # reading or changing migration history.
            if self._lock_statement is not None:
                cursor.execute(self._lock_statement)

            self._create_metadata_table(cursor)
            cursor.execute("SELECT version, name FROM neon_schema_migrations ORDER BY version")
            applied = tuple((int(version), name) for version, name in cursor.fetchall())
            known = {migration.version: migration.name for migration in self._migrations}
            for version, name in applied:
                if version not in known:
                    raise RuntimeError(f"database has unknown migration version {version}")
                if known[version] != name:
                    raise RuntimeError(f"migration name mismatch for version {version}")

            applied_versions = {version for version, _ in applied}
            expected = set(range(1, max(applied_versions, default=0) + 1))
            if applied_versions != expected:
                raise RuntimeError("database migration history is not contiguous")

            for migration in self._migrations:
                if migration.version in applied_versions:
                    continue
                expected_version = max(applied_versions, default=0) + 1
                if migration.version != expected_version:
                    raise RuntimeError(
                        f"migration history requires version {expected_version} before {migration.version}"
                    )
                for index, statement in enumerate(migration.statements):
                    cursor.execute(statement)
                    if index == 0 and migration.validate_after_first_statement is not None:
                        migration.validate_after_first_statement(cursor)
                self._insert_applied(cursor, migration)
                applied_versions.add(migration.version)

            connection.commit()
            return max(applied_versions, default=0)
        except Exception:
            rollback = getattr(connection, "rollback", None)
            if rollback is not None:
                rollback()
            raise
        finally:
            close_cursor = getattr(cursor, "close", None)
            if close_cursor is not None:
                close_cursor()
            connection.close()
