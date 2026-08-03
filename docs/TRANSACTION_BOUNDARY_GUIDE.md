# Transaction boundary guide

The Increment 3 coordinator is the sole commit and rollback owner.

A correction transaction contains:

1. trusted-tenant target resolution;
2. permission, reason, state and expected-version validation;
3. replacement/amendment/correction creation;
4. prior-version supersession or compatibility projection;
5. registry registration/retirement;
6. append-only Operational Event;
7. one final commit.

Owning services may flush to obtain identifiers or enforce ordering, but MUST NOT
commit or roll back. Any registry, projection or event failure rolls back every
earlier step. Session-level tenant, aggregate and immutability enforcement remains
active during each flush.

An idempotent command claims and completes its ledger row inside this same
transaction. Completion is flushed only after the business result and event are
valid; rollback removes the claim, permitting a deterministic retry. Services do
not open a nested transaction to escape a conflict.

External effects still require a future transactional outbox. Phase 1.5 makes
database state and Operational Events atomic, but does not claim atomic email,
file delivery, webhooks or message-broker publication.
