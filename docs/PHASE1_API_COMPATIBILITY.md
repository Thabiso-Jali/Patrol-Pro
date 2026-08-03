# Phase 1 API compatibility

## Increment 6 additive concurrency headers

Affected mutation payloads remain valid. Conflict-sensitive update/archive
routes accept optional `If-Match: <record_version>` and affected responses expose
`record_version`. Retry-prone creation and checkpoint confirmation accept optional
`Idempotency-Key`. The fallback may be retired only after all shipped clients
consistently provide these headers.

Phase 1 introduces canonical persistence and internal services without exposing incomplete workflows.

## Supported compatibility surface

- `/api/v1/customers` remains the commercial Customer API.
- `/api/v1/patrols` remains the Patrol Occurrence compatibility API.
- `/api/v1/alerts` remains the Incident compatibility API.
- `/api/v1/checkpoints/{id}/verify` remains supported and now records an append-only verification event.
- `/api/v1/users/officers` remains supported while resolving workforce identity through Employee profiles internally.
- `/api/v1/audit-logs` remains the compatibility read surface for the Operational Event Store.
- `/api/v1/notifications` remains supported and gains internal delivery-event fields without changing existing response requirements.

## Deliberately internal in Phase 1

No public router or frontend workflow is introduced for Sites, Contacts, Site Assets, Post Orders, Company Policies, Qualifications, Licences, Availability, Leave, Shifts, Patrol Templates, Evidence, Operational Alerts, Daily Activity Reports or the Domain Object Registry.

These models exist to prevent future schema fragmentation. A public API requires a complete permission, pagination, validation, error, audit and product workflow review.

## Phase 1.5 integrity compatibility

- `/teams`, `/patrols`, tracking and checkpoint confirmation retain their current
  request and response contracts.
- Legacy `user_id`/`officer_user_id` fields remain authoritative compatibility
  inputs. Services also write the same-tenant canonical `employee_id` and record
  whether it came from a canonical mapping or remains legacy-only.
- `record_version`, idempotency records, integrity checksums, snapshots and
  correction metadata are internal and are not added to existing response schemas.
- Existing legacy checkpoint `verified` state remains compatibility-only. Derived
  Verification Events remain `legacy_low_assurance`; the migration never upgrades
  them to stronger physical-presence evidence.
- No new Phase 1 resource receives a public endpoint in Increment 4.
