# Phase 1.5 Increment 4 migration notes

Revision `f15a4c9d7e21` follows `c6b03fd24b2a` and is the only Increment 4
revision. It drops no Phase 1 table or column.

Upgrade order:

1. Validate stored states, active-version duplicates and workforce mappability.
2. Add nullable/additive structures and version defaults.
3. Backfill Employee compatibility references using both User and organisation.
4. Verify every populated legacy workforce bridge was mapped.
5. Add checks, unique indexes and tenant-aware relationships.
6. Remove migration-only defaults where runtime values must be explicit.

Unexpected values or ambiguous mappings stop the transaction. Operators must
investigate and correct source data explicitly; the migration has no “pick one” or
data-deletion path.
