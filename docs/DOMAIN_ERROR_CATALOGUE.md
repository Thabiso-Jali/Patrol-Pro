# Domain error catalogue

| Code | Retryable | Meaning |
|---|---:|---|
| `CONCURRENT_MODIFICATION` | yes | The scoped record version changed. |
| `EXPECTED_VERSION_REQUIRED` | no | A high-risk command omitted its version. |
| `INVALID_EXPECTED_VERSION` | no | Version syntax or value is invalid. |
| `DUPLICATE_ASSIGNMENT` | no | Staffing overlaps or duplicates an assignment. |
| `IDEMPOTENT_REPLAY` | no | Informational replay outcome where surfaced. |
| `IDEMPOTENCY_IN_PROGRESS` | yes | The scoped command is executing. |
| `IDEMPOTENCY_KEY_REUSED` | no | The key fingerprint differs. |
| `DUPLICATE_VERIFICATION` | no | A separate confirmation duplicated a fact. |
| `ACTIVE_VERSION_CONFLICT` | yes | Another version won activation. |
| `ARCHIVE_CONFLICT` | yes | State or dependencies changed before archival. |
| `PERSISTENCE_FAILURE` | yes | Unknown persistence failure; details withheld. |

Envelopes never expose SQL, tables, constraints, raw database messages,
credentials, or the existence of another tenant's object.
