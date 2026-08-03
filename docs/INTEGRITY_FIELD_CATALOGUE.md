# Phase 1.5 integrity field catalogue

## Optimistic versions

`record_version` is present on Organisation, Customer, Site, Employee, Team,
Shift, Shift Assignment, Patrol Template, Patrol Occurrence, Incident,
Operational Alert, Notification, Evidence Attachment, Daily Activity Report,
Company Policy, Post Order and Post Order Version. Existing Shift, Patrol and
Incident fields are retained; the migration adds missing fields with initial value
1. Increment 6 implements expected-version handling through the shared
concurrency service and additive `If-Match` compatibility header.

Operational Events, Checkpoint Verification Events, Evidence Links, Operational
Event Subjects and acknowledgements are append-only or association facts and do
not receive optimistic versions.

## Stored state constraints

Application metadata derives allowed stored values from
`app.domain.states.STATE_MACHINES`. The migration contains a frozen release
snapshot. Transition edges are not database checks. Legacy checkpoint values are
an explicit exception because `verified` describes compatibility state, not strong
verification assurance.

## Replay protection

`idempotency_records` is unique by organisation, actor scope, command type and
key. It stores only a request fingerprint, safe result metadata, correlation and
retention timestamps. It is internal and tenant context never comes from a client
payload.

## Integrity and history metadata

- Verification Events: event kind, key, original/correction references, provenance
  and bounded context snapshot.
- Evidence: correction/supersession, acceptance actor/version/time, immutable and
  archive timestamps.
- Daily reports: correction/supersession, approval actor/version/time, checksum,
  site snapshot and archive timestamp.
- Post Order versions: content checksum and archive timestamp.
- Patrol Occurrences: operational snapshot in addition to template snapshot.

PostgreSQL is authoritative for partial indexes and added tenant-composite foreign
keys. SQLite `Base.metadata` schemas include supported constraints, but SQLite
cannot add every named constraint to an existing table without destructive table
rebuilds; migration parity tests therefore run on PostgreSQL 15.

## Increment 6 use

`record_version` is incremented exactly once by owning services for current
compatible writes; stale supplied versions return `CONCURRENT_MODIFICATION`.
Correction and
supersession fields are written only by controlled services. Snapshot and checksum
fields become protected when their record crosses its operational boundary.
