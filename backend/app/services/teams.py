from sqlalchemy.orm import Session

from .. import models
from ..domain.errors import ArchiveConflict
from .concurrency import advance_version, lock_tenant_record
from .tenant_validation import aggregate_mutation
from .transactions import require_transaction


def archive_team(
    db: Session, *, organisation_id: int, team_id: int,
    actor_user_id: int, expected_version: int | None,
) -> models.Team:
    require_transaction(db)
    team = lock_tenant_record(
        db, models.Team, record_id=team_id, organisation_id=organisation_id,
        relationship='Team', allow_archived=False,
    )
    assignment = db.query(models.PatrolAssignment.id).join(
        models.Patrol, models.Patrol.id == models.PatrolAssignment.patrol_id,
    ).filter(
        models.PatrolAssignment.organisation_id == organisation_id,
        models.PatrolAssignment.team_id == team.id,
        models.Patrol.lifecycle_status.in_({'draft', 'scheduled', 'in_progress'}),
    ).with_for_update().first()
    if assignment:
        raise ArchiveConflict()
    with aggregate_mutation(db, 'teams'):
        team.status = 'archived'
        team.is_deleted = True
        team.updated_by = actor_user_id
        advance_version(team, expected_version)
        db.flush()
    return team
