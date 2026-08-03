# Phase 1 compatibility bridge register

Existing callers may temporarily omit `If-Match` and `Idempotency-Key`, but
omission never disables tenant scoping, root/resource locks, overlap checks or
database uniqueness. New clients should provide current versions and stable keys
for retry-prone commands.

| Bridge | Compatibility field | Canonical field | Backfill/provenance | Retirement condition |
|---|---|---|---|---|
| Team membership | `team_members.user_id` | `employee_id` | Same-tenant `Employee.user_id`; `canonical_user_mapping` or `legacy_user_only` | Complete Employee workflow and client migration |
| Patrol assignment | `patrol_assignments.user_id` | `employee_id` | Same rule; team targets remain unchanged | Canonical occurrence assignment API complete |
| Officer location | `officer_locations.officer_user_id` | `employee_id` | Same rule; no guessed mapping | Canonical workforce identity adopted by tracking |
| Checkpoint status | `checkpoints.status='verified'` | Verification Event | Existing event provenance is `legacy_low_assurance` | Compatibility readers retired after assurance workflow |
| Patrol | `patrols` table/API | Patrol Occurrence | Physical table retained; canonical lifecycle/snapshots additive | Versioned API transition plan |
| Incident | `alerts` table/API | Incident aggregate | Physical table retained | Explicit incident API migration |

Every bridge lookup is organisation-scoped. An upgrade stops when a populated
User-based bridge has no single same-tenant Employee mapping. Legacy fields are not
dropped by the Phase 1.5 integrity revision.

Increment 5 compatibility writes are projections only. Checkpoint `verified_at`
and `verified_by` are updated by the canonical verification service in the same
transaction as the append-only Verification Event. `/alerts` delegates mutations
to the Incident service. `/patrols` retains mutable non-terminal behaviour but
terminal occurrences require amendments and compatibility deletion becomes a
truthful cancellation rather than erasing the row.
