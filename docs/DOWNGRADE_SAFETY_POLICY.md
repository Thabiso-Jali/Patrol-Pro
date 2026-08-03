# Phase 1.5 downgrade safety policy

Downgrade to Phase 1 is supported only for a backfill-only database. The revision
refuses downgrade if:

- the idempotency ledger contains any command record;
- a mutable aggregate has advanced beyond version 1;
- an Employee reference cannot be represented by its same-tenant legacy User;
- any correction, approval, acceptance, checksum, immutable/archive or snapshot
  metadata would be lost;
- a native verification event depends on Phase 1.5 provenance; or
- any other post-migration operational fact cannot be reconstructed in Phase 1.

Refusal raises an explicit `Phase 1.5 integrity migration refused` error inside the
database transaction. It never deletes rows or uses cascade behaviour to make a
rollback pass. After the blocking records are retained in a compatible successor
system or the rollback is abandoned, normal forward migration remains safe.
