# State-transition catalogue

`backend/app/domain/states.py` is executable and authoritative. This document is
an operator-readable index, not a second transition definition.

- Draft and pre-operational states permit only catalogue transitions.
- Immutable catalogue states require replacement, amendment, correction or
  supersession services even when a transition edge exists.
- Incident reopening is a controlled exceptional correction requiring expected
  state/version, elevated permission and reason.
- Future-effective Policy and Post Order versions stay `approved` until their
  activation time.
- Compatibility checkpoint `verified` is not a strong-assurance state and never
  changes the provenance of its Verification Event.

Any catalogue change requires service, database stored-state, permission,
compatibility and migration review.
