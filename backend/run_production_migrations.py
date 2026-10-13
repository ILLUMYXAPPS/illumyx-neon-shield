"""Explicit production migration command; never run migrations at app startup.

Run with `python -m backend.run_production_migrations` from a deployment job
after database configuration and credentials have been injected. This command
never prints connection URLs, credentials, SQL, or driver exception details.
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from backend.migrations import MigrationRunner
from backend.production_config import MigrationConfig, validate_migration_config
from backend.production_migrations import PRODUCTION_MIGRATIONS
from backend.secrets import EnvironmentSecretProvider, SecretProvider


def _connection_factory(config: MigrationConfig) -> Callable[[], Any]:
    """Create a lazy PostgreSQL connector using validated TLS and separate secrets."""
    def connect() -> Any:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "production PostgreSQL support requires psycopg; install backend/requirements-production.txt"
            ) from exc
        return psycopg.connect(
            config.database_url,
            user=config.database_user,
            password=config.database_password,
            connect_timeout=10,
            application_name="illumyx-neon-shield-migrations",
        )

    return connect


def run_migrations(
    *,
    config: MigrationConfig | None = None,
    env: dict[str, str] | None = None,
    secret_provider: SecretProvider | None = None,
    connection_factory: Callable[[], Any] | None = None,
) -> int:
    """Validate migration-specific production configuration, apply, and verify.

    Dependency injection is provided for deterministic tests. Production CLI
    calls resolve only the database credentials needed for the migration job.
    """
    if config is None:
        provider = secret_provider or EnvironmentSecretProvider(env)
        config = validate_migration_config(env, secret_provider=provider)

    connect = connection_factory or _connection_factory(config)
    runner = MigrationRunner(
        connect,
        PRODUCTION_MIGRATIONS,
        placeholder="%s",
        lock_statement="SELECT pg_advisory_xact_lock(1180194898, 1)",
    )
    expected_version = max((migration.version for migration in PRODUCTION_MIGRATIONS), default=0)
    applied_version = runner.apply_pending()
    if applied_version != expected_version:
        raise RuntimeError("production migration runner returned an unexpected schema version")

    verified_version = runner.current_version()
    if verified_version != expected_version:
        raise RuntimeError("production database schema version verification failed")
    return verified_version


def main() -> int:
    try:
        version = run_migrations()
    except Exception as exc:  # Do not print driver errors that may contain deployment details.
        print(
            "Production database migrations failed closed "
            f"(error_type={type(exc).__name__}); inspect secured deployment logs.",
            file=sys.stderr,
        )
        return 1

    print(f"Production database migrations complete: schema_version={version}; status=verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
