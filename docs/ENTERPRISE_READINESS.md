# Patrol Pro enterprise readiness record

Patrol Pro is an MVP intended for controlled demonstration and pilot evaluation. It is not currently approved as the sole system for live security operations.

## Decision and scope

The supported SaaS path is the FastAPI, React, and PostgreSQL stack in
`backend/`, `frontend/`, and `render.yaml`. The PHP/MySQL application in
`php-app/` is a separate legacy implementation. It has a different identity
model and contains demonstration seed records. It must not be connected to the
SaaS production database. Its data needs an explicit, rehearsed migration or a
documented decommission decision.

This change establishes the company and identity boundary. It does not
establish enterprise operational readiness for the whole repository.

## Implemented foundation

- A signup creates one company and one `company_owner` in one transaction.
- Public employee self-registration and direct password-based employee
  creation are disabled.
- Employees join a specific company through a random, hashed, expiring,
  single-use invitation.
- Every operational model has a required company foreign key.
- Shared CRUD scoping fails closed when a company identifier is absent.
- Access and refresh tokens bind user ID, company ID, canonical role,
  permission version, session version, expiry, and token type.
- Logout increments the server-side session version, revoking previously
  issued access and refresh tokens.
- Disabled users, deleted users, inactive companies, changed permissions, and
  locked accounts are rejected during authentication.
- Audit records carry a direct company foreign key.
- Dashboard day boundaries use the company's IANA timezone.
- Previously seeded React dashboard/module records were removed.

The invitation response currently returns the raw token once because there is
no transactional email provider. A production mail service should construct a
short-lived acceptance URL and the API must stop returning the token to
interactive administrative clients once that service exists.

## Authorisation model

| Role | Intended scope |
| --- | --- |
| Company Owner | Company settings, administrators, all company operations |
| Administrator | User administration and all company operations |
| Manager | Invitations, operations, reports, and audit viewing |
| Supervisor | Operations and reports |
| Employee | Assigned operational work |
| Read Only | Operations and reports without writes |

`admin` and `officer` remain temporary database/token aliases for
`administrator` and `employee`. Remove those aliases only after existing rows
have been migrated and active sessions have expired.

## Migration safety

Revision `c3e74a9d52f1` adds the ownership/session/invitation schema. It refuses
to continue if an existing operational or audit row has no company. This is
intentional: guessing ownership would create a cross-tenant disclosure risk.
Operators must identify and assign any such rows before retrying. No row is
deleted or reassigned automatically.

The migration chain was validated from an empty PostgreSQL 15 database with
`alembic upgrade head`, followed by `alembic check`.

## Known gaps and release gates

The following remain blockers for an enterprise production claim:

- Most frontend modules are still concentrated in `App.js`; several edit flows
  remain client-only and need API-backed persistence or honest read-only empty
  states.
- No WebSocket/SSE event bus, connection recovery protocol, or horizontally
  scalable pub/sub layer exists.
- No offline command queue, IndexedDB persistence, idempotency key model,
  conflict-resolution UI, or background-sync policy exists.
- The rate limiter is process-local and must move to a shared store before
  multi-instance operation.
- Refresh tokens are revocable through a session version but are not stored as
  individually hashed, rotating sessions with reuse detection.
- Invitation delivery, password reset, email verification, MFA, and SSO are
  not implemented.
- No PostgreSQL row-level-security policy provides defence in depth.
- No worker queue exists for reports, notifications, escalation, or integration
  jobs.
- No central structured logging, tracing, alerting, SLOs, backup-restore
  rehearsal, penetration test, accessibility audit, or load test is evidenced.
- The deployment blueprint is a demonstration configuration, not a
  high-availability topology.
- Legacy PHP seed data remains inside the isolated legacy tree.

## Target architecture

Keep the application as a modular monolith until module boundaries and load
measurements justify extraction:

1. API modules own schemas, permissions, service logic, and repositories.
2. PostgreSQL is the source of truth; all tenant tables use required company
   keys and indexed tenant/time access paths.
3. Redis provides shared rate limiting, ephemeral presence, job coordination,
   and WebSocket fan-out.
4. A worker tier handles report generation, notification delivery, escalation,
   and external integrations with idempotent jobs.
5. An outbox table publishes committed domain events; clients resume from an
   event cursor after reconnect.
6. Offline clients queue idempotent commands in IndexedDB, show sync state, and
   surface server conflicts instead of silently overwriting data.
7. Object storage holds documents using company-prefixed keys, short-lived
   signed URLs, malware scanning, and immutable retention where required.

## Delivery sequence

1. Finish API-backed users, incidents, checkpoints, reports, and settings;
   split the React application by feature and add permission-aware routes.
2. Add rotating hashed refresh sessions, verification/reset/MFA workflows,
   invitation email, shared rate limiting, and PostgreSQL RLS tests.
3. Add an outbox, Redis, workers, WebSocket resume cursors, and mobile
   reconnect behaviour.
4. Add offline idempotency, encrypted local data policy, conflict handling, and
   queued evidence upload.
5. Add document storage, audit export/retention, integrations, observability,
   backup restoration, load testing, accessibility testing, and security
   review.

Every phase requires tenant-isolation, permission, migration, rollback, and
failure-mode tests before release.
