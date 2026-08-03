# Correction and immutability policy

Controlled correction, reopening, acceptance and approval commands are
conflict-sensitive. They require an expected version where the target is mutable
and follow the canonical lock order. An idempotent replay never creates a second
correction or Operational Event.

| Record | Mutable boundary | Controlled change | Permission |
|---|---|---|---|
| Company Policy | Draft/approved; content immutable when active | New version, atomic activation/supersession | `company.manage` |
| Post Order Version | Draft/approved; content immutable when active | New version tied to the Post Order | `company.manage` |
| Shift | Draft through active legal transitions | Amendment after completed/cancelled | `patrols.manage` |
| Shift Assignment | Proposed through active legal transitions | Replacement correction after completed/cancelled | `patrols.manage` |
| Patrol Template | Draft; content immutable when active | Replacement template version | `patrols.manage` |
| Patrol Occurrence | Draft/scheduled/in progress | Amendment after completed/missed/cancelled | `patrols.manage` |
| Incident | Open/investigating | Controlled reopening or append-only correction after resolution | `incidents.manage` |
| Evidence Attachment | Workflow fields before available | Replacement attachment; original superseded | `operations.write` |
| Daily Activity Report | Draft | New revision after generation | `reports.read` |
| Verification/Operational Event | Append-only immediately | New correction event | Owning domain permission |

Every correction uses a trusted organisation, closed `DomainObjectType`, target ID,
bounded reason code and explanation, actor, required permission, expected version
or state where applicable, and correlation ID. Cross-tenant failures do not reveal
whether the target exists.

Hard deletion of operational history is forbidden. Registry retirement remains
referentially safe and archived parents reject new operational children. Restore
is never inferred from a status edit.
