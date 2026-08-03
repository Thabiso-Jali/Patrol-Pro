from sqlalchemy.orm import Session

from .. import models
from ..domain.corrections import CorrectionCommand
from ..domain.errors import ImmutableRecord
from ..domain.registry import DomainObjectType
from .corrections import emit_correction_event, validate_correction_target
from .domain_registry import register_domain_object
from .tenant_validation import aggregate_mutation, require_tenant_record


def replace_patrol_template(
    db: Session, *, template_id: int, command: CorrectionCommand,
    name: str | None = None, route_description: str | None = None,
    required_employees: int | None = None, expected_duration_minutes: int | None = None,
    instructions: str | None = None,
):
    original = require_tenant_record(
        db, models.PatrolTemplate, record_id=template_id,
        organisation_id=command.organisation_id, relationship='Patrol Template',
        allow_archived=True,
    )
    validate_correction_target(db, command=command, record=original, object_type=DomainObjectType.PATROL_TEMPLATE)
    if original.status != 'active':
        raise ImmutableRecord('patrol_template', original.status)
    replacement = models.PatrolTemplate(
        organisation_id=command.organisation_id, site_id=original.site_id,
        name=name if name is not None else original.name,
        route_description=route_description if route_description is not None else original.route_description,
        required_employees=required_employees if required_employees is not None else original.required_employees,
        expected_duration_minutes=(expected_duration_minutes if expected_duration_minutes is not None else original.expected_duration_minutes),
        instructions=instructions if instructions is not None else original.instructions,
        status='draft', version=original.version + 1, supersedes_id=original.id,
    )
    with aggregate_mutation(db, 'patrol_templates'):
        db.add(replacement)
        db.flush()
    register_domain_object(
        db, organisation_id=command.organisation_id,
        object_type=DomainObjectType.PATROL_TEMPLATE, object_id=replacement.id,
    )
    emit_correction_event(
        db, command=command, object_type=DomainObjectType.PATROL_TEMPLATE,
        record=original, action='patrol_template.replacement_created',
        additional_metadata={'replacement_id': replacement.id},
    )
    return replacement
