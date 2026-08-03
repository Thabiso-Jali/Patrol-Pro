# Concurrency and idempotency guide

## Expected versions

`If-Match` accepts a positive integer, quoted integer, or weak ETag such as
`W/"3"`. Malformed values return `INVALID_EXPECTED_VERSION`. A stale value
returns `CONCURRENT_MODIFICATION` only after tenant-scoped resolution. Controlled
correction and reopening commands require an expected version.

Successful mutable aggregate commands increment `record_version` exactly once.
Failed commands and compatibility projections do not independently advance it.
Append-only facts remain unversioned.

## Idempotency

`Idempotency-Key` is additive for current compatibility clients and required for
new clients retrying consequential commands. Keys are trimmed, limited to 128
safe characters, and scoped by organisation, trusted actor, and server-derived
command type. Client payloads never supply organisation or actor.

The fingerprint is SHA-256 over canonical allow-listed command data. Passwords
contribute only a digest; raw passwords, tokens, bodies, evidence, care data and
credentials are never stored. Safe result metadata is limited to 4096 bytes.

- matching completed command: replay the authoritative resource without an event;
- different fingerprint: `IDEMPOTENCY_KEY_REUSED`;
- pending duplicate: retryable `IDEMPOTENCY_IN_PROGRESS`;
- rolled-back command: claim rolls back and a retry may execute;
- completed records: retained for at least 30 days; `expires_at` marks cleanup
  eligibility, and retained rows replay until trusted maintenance removes them;
  there is no public management API.

## Lock order

1. Organisation where an organisation-wide invariant requires it.
2. Aggregate root or stable identity.
3. Parent operational record.
4. Teams, Users, and Employees sorted by numeric ID.
5. Child assignments or version rows sorted by ID.
6. Domain Object Registry record.
7. Idempotency ledger row.
8. Append-only Operational Event insertion.

Ordinary updates use optimistic versions plus a root lock. Staffing, checkpoint
confirmation, version activation, acceptance, approval and archive/dependency
workflows use targeted locks for multi-row invariants. No external work may run
while locks are held.

PostgreSQL 15 is authoritative for concurrency. SQLite verifies contracts and
rollback behaviour but cannot prove lock scheduling or partial-index arbitration.

Internal Employee, Team and Site archive commands use the same locks as staffing
and operational-child creation. Their public workflows remain intentionally
absent; the services enforce aggregate invariants without exposing unfinished APIs.
