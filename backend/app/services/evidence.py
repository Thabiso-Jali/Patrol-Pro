from sqlalchemy.orm import Session

from .. import models
from .domain_registry import require_domain_object


def link_evidence(
    db: Session,
    *,
    organisation_id: int,
    evidence_attachment_id: int,
    domain_object_id: int,
    linked_by_employee_id: int | None,
) -> models.EvidenceLink:
    evidence = db.query(models.EvidenceAttachment).filter(
        models.EvidenceAttachment.id == evidence_attachment_id,
        models.EvidenceAttachment.organisation_id == organisation_id,
    ).first()
    if not evidence:
        raise ValueError('Evidence does not exist in this organisation')
    require_domain_object(db, organisation_id=organisation_id, domain_object_id=domain_object_id)
    link = models.EvidenceLink(
        organisation_id=organisation_id,
        evidence_attachment_id=evidence.id,
        domain_object_id=domain_object_id,
        linked_by_employee_id=linked_by_employee_id,
    )
    db.add(link)
    db.flush()
    return link
