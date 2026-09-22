# Neon Shield Production Infrastructure Readiness

This document is a repository-side runbook for the production infrastructure gate tracked by Issue #36.

It does **not** provision infrastructure, store credentials, change application features, or authorize Apple signing/release configuration.

## Scope

The production gate has four infrastructure requirements:

1. HTTPS deployment
2. Managed PostgreSQL persistence
3. Production secret management
4. Production monitoring and security-event delivery

The repository already contains the application-side boundaries for these requirements. Real infrastructure evidence is still required before Issue #36 can be marked complete.

## Required production configuration

Production configuration must use:

- `NEON_AUTH_ENV=production`
- `NEON_AUTH_DB` pointing to managed PostgreSQL
- `NEON_IDP_URL` using HTTPS
- `NEON_IDP_CLIENT_ID`
- `NEON_MONITORING_ENDPOINT` using HTTPS
- `NEON_IDP_CLIENT_SECRET` supplied only through the injected secret provider
- `NEON_DB_PEPPER` supplied only through the injected secret provider

The production validator rejects SQLite/local database URLs, non-PostgreSQL databases, database connections without explicit TLS, non-HTTPS identity-provider URLs, and non-HTTPS monitoring endpoints.

## Deployment sequence

### 1. Managed PostgreSQL

Provision a managed PostgreSQL database outside this repository.

Before production use, verify:

- encryption at rest is enabled;
- database access uses least privilege;
- network access is restricted to the deployment environment;
- TLS is required for application connections;
- versioned migrations are applied explicitly;
- backups are enabled;
- backup retention is configured;
- restore capability is available.

Do not put the database password or connection string in source control.

### 2. Secret management

Store production secrets in the deployment platform's protected secret store or an equivalent dedicated secret manager.

Required secret values:

- `NEON_IDP_CLIENT_SECRET`
- `NEON_DB_PEPPER`

Do not commit, print, echo, or place production secret values in workflow files.

Where GitHub Actions is used for deployment, prefer a protected `production` environment so secrets are only exposed to an approved production job.

### 3. HTTPS

Deploy the backend behind a managed TLS edge/reverse proxy.

Verify:

- public traffic reaches the service only through HTTPS;
- the TLS certificate is valid;
- the production identity-provider endpoint is HTTPS;
- the monitoring endpoint is HTTPS;
- the backend's local-only HTTP binding is not directly exposed;
- `GET /health` succeeds through the production HTTPS endpoint.

Record the production endpoint and UTC verification time in the release evidence record. Do not record secrets.

### 4. Monitoring and security alerts

Configure `NEON_MONITORING_ENDPOINT` to the real production monitoring/security-event destination.

Verify delivery using safe test events.

At minimum, verify that:

- authentication abuse/rate-limit events can be observed;
- security-monitoring failures are observable;
- database/backend failures are observable;
- alert delivery reaches the intended operational destination;
- logs and alerts do not contain passwords, bearer tokens, raw session tokens, or raw device identifiers.

### 5. Backup and recovery evidence

Before production launch, perform a restore test in an isolated recovery environment.

Minimum recovery targets defined by the repository contract:

- RPO: no more than 15 minutes
- RTO: restore service within 60 minutes
- backup retention: at least 35 days, subject to legal/operational requirements

The restore record must identify:

- backup identifier;
- UTC restore timestamp;
- restored schema version;
- application-level verification result;
- data-integrity verification result.

Never overwrite the known-good production database as part of the restore test.

## Evidence record

Use this checklist only after real infrastructure has been provisioned and tested.

- [ ] Managed PostgreSQL provisioned
- [ ] PostgreSQL TLS verified
- [ ] Production migrations applied
- [ ] Backup policy verified
- [ ] Restore test completed
- [ ] Production secrets stored outside source control
- [ ] Secret-boundary/fail-closed checks passed
- [ ] HTTPS endpoint verified
- [ ] Direct backend exposure checked
- [ ] Monitoring endpoint verified
- [ ] Security alert delivery verified
- [ ] Production smoke test completed
- [ ] Evidence timestamps recorded in UTC
- [ ] Issue #36 updated with evidence

## Release boundary

Do **not** mark Issue #36 complete from repository tests alone.

Repository tests prove the configuration and application contracts. They do not prove that a real database, HTTPS endpoint, secret store, monitoring destination, backup system, or restore environment exists.

No Apple signing, provisioning, certificate, TestFlight, or iOS release configuration is part of this infrastructure gate.
