# Phase 1.5 readiness checklist

- [x] Canonical aggregate ownership and registry
- [x] Tenant/session enforcement
- [x] Transaction coordinator as sole commit owner
- [x] Integrity migration `f15a4c9d7e21`
- [x] Optimistic version storage
- [x] Stored-state constraints
- [x] Internal idempotency ledger structure
- [x] Central immutability policy
- [x] Bounded correction command
- [x] Append-only Verification and Operational Events
- [x] Policy/Post Order replacement workflows
- [x] Shift/Patrol amendments
- [x] Evidence/Report revision protection
- [x] Compatibility projection preservation
- [x] Expected-version API headers and command idempotency execution — Increment 6
- [x] Deterministic row-lock order for conflict-sensitive workflows
- [x] Stable concurrency and replay error catalogue
- [x] PostgreSQL races for staffing, lifecycle transitions, active versions,
  evidence/report commands, archive conflicts and registry retirement
- [ ] Public APIs for unfinished canonical resources — require complete workflows

Increment 6 adds no frontend capability and exposes no unfinished router.
