# Phase 1 API compatibility

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
