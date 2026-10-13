# Neon Shield production release gates

Status: **not production-ready**. This document is an operational acceptance checklist, not evidence that any production service has been provisioned or tested. Complete each gate with a dated record tied to an exact commit SHA. Never paste secrets, tokens, connection strings, private user data, or unredacted production logs into issues or pull requests.

## 1. Required evidence record

For every gate, record:

- Repository and exact commit SHA tested.
- Environment type (disposable integration, staging, or production) and provider/service version.
- Exact command or workflow URL and its result.
- Expected versus actual outcome, including failure and recovery results.
- Reviewer/operator and date.
- Any skips, warnings, or limitations.

A green CI run proves only the scenarios exercised by that run. It does not prove a managed-provider deployment, operational monitoring, or mobile-device behaviour.

## 2. Managed PostgreSQL acceptance

- [ ] Provision a **disposable/staging** PostgreSQL instance with TLS enabled; do not use production data for qualification.
- [ ] Use a dedicated least-privilege database role. Confirm its permissions are sufficient for the reviewed migration and application operations, but not database administration.
- [ ] Supply credentials through the chosen deployment secret manager. Keep credentials separate from the database URL; never print environment variables or connection details.
- [ ] Confirm the URL has an explicit supported TLS mode; prefer certificate and hostname verification (`sslmode=verify-full`) when supported by the provider.
- [ ] Run the PostgreSQL integration suite against the provider-compatible staging instance. Include concurrent audit appends, migration idempotency, failed-write rollback, and audit-chain/head consistency.
- [ ] Record provider/version, connection settings with secrets redacted, test counts, output, and exact SHA.
- [ ] Simulate a database interruption and verify bounded failure behaviour, reconnection/recovery, and that no audit-chain fork or lost committed event occurs.

The existing PostgreSQL 16 CI workflow uses an isolated test service. It is useful integration evidence, but it is not a managed-provider smoke test.

## 3. Versioned migration deployment contract

The repository has `MigrationRunner` and `PRODUCTION_MIGRATIONS`; the PostgreSQL store factory intentionally does not run migrations at application startup. Before deployment, provide and review a deployment entry point/job that explicitly:

1. Uses the approved secret provider to obtain the database connection configuration without printing it.
2. Opens a PostgreSQL connection using the same TLS and connection policy as the application.
3. Instantiates `MigrationRunner(connection_factory, PRODUCTION_MIGRATIONS, placeholder="%s")`.
4. Calls `apply_pending()` and fails the deployment on any exception or unexpected migration version.
5. Records the resulting schema version and redacted success/failure metadata.
6. Runs before the new application version receives traffic, with a single controlled migration job rather than every application replica racing to migrate.

Acceptance checks:

- [ ] A fresh disposable database reaches the expected migration version.
- [ ] Running the migration job a second time is idempotent.
- [ ] An injected migration failure leaves no partially applied migration and fails closed.
- [ ] An unknown version, name mismatch, or non-contiguous history blocks deployment.
- [ ] The deployment job's exact command and logs are attached as redacted evidence.
- [ ] Backup/restore and recovery steps are documented and tested before production data is introduced.

**Important:** Do not claim this gate is closed merely because migration unit/integration tests pass. A deployment entry point and an actual run against the intended provider still need to be demonstrated.

## 4. Secrets, connections, and recovery

- [ ] Use a real secret manager or platform secret store with least-privilege access and documented rotation.
- [ ] Confirm the production identity-provider secret is actually consumed by the selected authentication path, or explicitly document and test the intended identity-provider integration boundary.
- [ ] Establish and load-test provider connection limits. The current adapter opens a connection per DB operation; it does not provide a connection pool.
- [ ] Set operational timeouts, connection limits, resource limits, and a documented outage/retry policy.
- [ ] Test backup restoration in an isolated environment, including audit-chain verification after restore.
- [ ] Verify that failures do not silently fall back to SQLite or an insecure development configuration.

## 5. Monitoring and readiness

- [ ] Inject real security-event and alert-sink implementations; do not use no-op sinks in production.
- [ ] Deliver test warning and critical events to the intended destination and confirm receipt, alert ownership, and escalation.
- [ ] Ensure telemetry excludes credentials, session tokens, raw device identifiers, and sensitive personal data.
- [ ] Keep liveness separate from readiness. A static HTTP `/health` response is not proof that PostgreSQL, migrations, or alert delivery are healthy.
- [ ] Define and test a readiness check that reports unavailable when required dependencies are unavailable, without exposing secrets or internal details.
- [ ] Test monitoring destination outage and alert-delivery failure handling.

## 6. Mobile end-to-end and vault recovery

- [ ] Install the debug beta on a representative Android device or suitable emulator; verify launch and app identity.
- [ ] Exercise sign-in, invalid credentials, session refresh, logout/revocation, and device trust behaviour against a controlled test backend.
- [ ] Verify vault encrypt/decrypt round trips and that the original file remains unchanged.
- [ ] Test unavailable secure storage, app reinstall, missing/lost vault key, corrupted encrypted data, interrupted writes, and restore from a separately retained original.
- [ ] Confirm errors fail safely and the app does not claim it can recover a vault whose key is lost.
- [ ] Record device/OS or emulator version, build SHA, steps, outcomes, and sanitized logs.

The debug-signed APK is for testing only. A successful build and signature verification do not substitute for running these scenarios or for Apple signing/certification.

## 7. Independent review and release decision

- [ ] An independent reviewer records the exact PRs/SHAs reviewed and their findings.
- [ ] Each finding is fixed or explicitly dispositioned with rationale and reviewer agreement.
- [ ] Relevant automated checks pass on the final reviewed commits.
- [ ] Managed-provider, migration, recovery, monitoring, and mobile evidence is complete.
- [ ] A release owner records a go/no-go decision and outstanding known limitations.

Until all applicable checks have evidence, keep changes unmerged and do not describe Neon Shield as production-ready. Do not bypass failed checks or merge stacked PRs out of dependency order.
