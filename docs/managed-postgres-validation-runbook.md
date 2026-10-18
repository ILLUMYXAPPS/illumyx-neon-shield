# Managed PostgreSQL staging validation runbook

Status: **planned, not yet executed against a managed provider**. This runbook defines a safe staging acceptance procedure. It does not prove that a provider, account, credentials, or staging database has been provisioned.

## Safety rules

- Use a disposable staging database with no real user data. Never point this procedure at production.
- Never put passwords, tokens, full connection strings, private data, or unredacted logs in GitHub issues, pull requests, terminal recordings, or test artifacts.
- Use a dedicated staging role with only the privileges needed for the application and reviewed migrations. Do not use a provider owner/admin role for routine tests.
- Store credentials in the chosen platform secret store. The current environment-backed provider is an interface boundary, not a cloud secret-manager integration.
- Stop on any unexpected schema version, TLS failure, privilege escalation requirement, audit-chain inconsistency, or unexplained data loss. Capture sanitized evidence and do not retry destructive steps against an unknown state.
- Record the exact code SHA for every run. Do not label CI-only tests as managed-provider validation.

## Gate A: provision and verify the staging environment

- [ ] Select and document the intended managed PostgreSQL provider and supported PostgreSQL version.
- [ ] Create an isolated, disposable staging database and a dedicated least-privilege role.
- [ ] Require TLS. Prefer `sslmode=verify-full` where the provider supports valid certificate and hostname verification; document any provider-specific TLS requirements.
- [ ] Keep the database URL free of embedded credentials. Supply username and password separately through the approved secret mechanism.
- [ ] Confirm connection, database name, TLS mode, role permissions, and provider connection limits without printing secrets.
- [ ] Record provider/service version, configuration summary with secrets redacted, date/operator, and the tested commit SHA.

**Pass criteria:** TLS is verified as intended, the role is least-privileged, connection succeeds, and no secret appears in output or artifacts.

## Gate B: migration deployment command

Run the reviewed command in a controlled deployment job, not as application startup work:

```sh
python -m backend.run_production_migrations
```

Use the staging configuration only. Do not paste the environment or command output containing connection details into GitHub.

- [ ] On a fresh schema, the command exits successfully and reports the expected schema version.
- [ ] Run it a second time; it remains successful and does not duplicate or corrupt migration history.
- [ ] Verify migration history is contiguous and matches the expected migration names and versions.
- [ ] Run two or more deployment jobs concurrently in the isolated staging database; confirm serialization and one complete migration history.
- [ ] In a disposable schema, inject a controlled migration failure; confirm a nonzero exit and no falsely reported success or partial committed migration.
- [ ] Confirm an unexpected schema version or invalid history fails closed.
- [ ] Verify logs include only sanitized status, version, and error type. Do not expose connection strings, credentials, SQL containing data, or raw driver exception messages.
- [ ] Confirm the deployment system runs migrations once before the new application version receives traffic.

**Pass criteria:** Every test has recorded expected and actual results, no silent partial success, and migration command exits accurately reflect success or failure.

## Gate C: audit-chain integrity and concurrency

Run the repository's PostgreSQL integration suite against the provider-compatible staging database, or a dedicated test schema/database. Do not run destructive integration tests against shared application data.

- [ ] Append audit events concurrently from multiple independent connections.
- [ ] Verify event ordering, chain-head consistency, and that no fork or committed event loss occurs.
- [ ] Confirm the production schema and writer agree on the canonical `audit_chain_head.event_hash` column; reject a stale existing head before migration 4 is recorded as applied.
- [ ] Confirm concurrent deployment jobs serialize through the transaction-scoped PostgreSQL advisory lock before inspecting migration history.
- [ ] Verify failed writes roll back atomically and do not advance the durable chain head incorrectly.
- [ ] Verify verifier behaviour for a valid chain, modified event, missing event, invalid head, and ambiguous history.
- [ ] Repeat relevant tests after migration and after a staging database restart.
- [ ] Record counts and sanitized results; do not upload real audit payloads if they contain personal or sensitive data.

**Pass criteria:** Chain verification and durable head agree after success, concurrency, failure, restart, and migration scenarios.

## Gate D: outage and recovery

Use only staging. Coordinate a controlled interruption with the provider's supported tools.

- [ ] Temporarily make the database unavailable or use a documented provider-supported fault simulation.
- [ ] Confirm requests fail within documented time limits and do not report false success.
- [ ] Restore connectivity and confirm recovery behaviour is bounded and observable.
- [ ] Verify committed audit events remain present and chain verification passes after recovery.
- [ ] Test the documented backup/restore process into a separate isolated database and verify the restored audit chain.
- [ ] Confirm no fallback to SQLite, local files, or development configuration occurs silently.

**Pass criteria:** Failure is bounded and visible, recovery is documented, committed data remains consistent, and restored data verifies. If the provider cannot safely simulate an outage, mark the case as skipped with the reason and arrange a provider-supported alternative. Do not claim it passed.

## Gate E: runtime configuration and operational readiness

- [ ] Inspect which environment values the migration command actually needs. It should not require unrelated identity-provider or monitoring configuration unless a documented security dependency requires them.
- [ ] Confirm the configured identity-provider integration is actually used by the selected authentication path, or document the intended boundary and keep the feature disabled until verified.
- [ ] Confirm the chosen secret store is a real platform/cloud integration with access controls and rotation; environment variables alone do not satisfy that gate.
- [ ] Confirm connection lifecycle, provider limits, timeouts, retry policy, and shutdown behaviour.
- [ ] Verify readiness reports unavailable when required dependencies are unhealthy, while liveness remains separate.
- [ ] Deliver a test security event and alert to the intended monitoring destination and verify receipt; test delivery failure without exposing sensitive data.

**Pass criteria:** Each production dependency has a real implementation, a documented owner, and a successful staging test. Placeholders, no-op sinks, and static health responses do not count.

## Evidence record template

Create one sanitized record per run:

- **Date/time and operator:**
- **Repository and exact commit SHA:**
- **Provider and PostgreSQL version:**
- **Environment/database identifier:** (non-secret label only)
- **TLS mode and role:** (no credentials)
- **Command/workflow and link:**
- **Scenario and expected result:**
- **Actual result and exit code:**
- **Schema version before/after:**
- **Audit-chain verification result:**
- **Outage/recovery or restore result:**
- **Warnings, skips, limitations:**
- **Independent witness/reviewer, if any:**
- **Pass / fail / blocked:**

## Go/no-go rule

The managed-database gate remains **BLOCKED** until Gates A-D have actual staging evidence. Gate E must be complete before production readiness can be claimed. CI against a disposable PostgreSQL service is useful supporting evidence, not a substitute. Keep the related pull requests unmerged pending independent review and the project's explicit approval process.
