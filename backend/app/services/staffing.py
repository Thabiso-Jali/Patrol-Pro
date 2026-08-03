from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas

OPERATIONAL_ROLES = {
    schemas.UserRole.officer.value,
    schemas.UserRole.employee.value,
}


def operational_users(db: Session, organisation_id: int):
    return (
        db.query(models.User)
        .filter(
            models.User.organisation_id == organisation_id,
            models.User.role.in_(OPERATIONAL_ROLES),
            models.User.is_active.is_(True),
            models.User.is_deleted.is_(False),
        )
        .order_by(models.User.full_name.asc(), models.User.id.asc())
        .all()
    )


def team_member_ids(db: Session, team_id: int, organisation_id: int) -> set[int]:
    return {
        row.user_id
        for row in db.query(models.TeamMember)
        .join(models.User, models.User.id == models.TeamMember.user_id)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.organisation_id == organisation_id,
            models.User.organisation_id == organisation_id,
            models.User.role.in_(OPERATIONAL_ROLES),
            models.User.is_active.is_(True),
            models.User.is_deleted.is_(False),
        )
    }


def conflicting_user_ids(
    db: Session,
    organisation_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_patrol_id: int | None = None,
) -> set[int]:
    patrol_query = db.query(models.Patrol.id).filter(
        models.Patrol.organisation_id == organisation_id,
        models.Patrol.is_deleted.is_(False),
        models.Patrol.start_time.is_not(None),
        models.Patrol.end_time.is_not(None),
        models.Patrol.start_time < end_time,
        models.Patrol.end_time > start_time,
    )
    if exclude_patrol_id is not None:
        patrol_query = patrol_query.filter(models.Patrol.id != exclude_patrol_id)
    patrol_ids = [row.id for row in patrol_query]
    if not patrol_ids:
        return set()

    assignments = db.query(models.PatrolAssignment).filter(
        models.PatrolAssignment.organisation_id == organisation_id,
        models.PatrolAssignment.patrol_id.in_(patrol_ids),
    ).all()
    conflicts = {assignment.user_id for assignment in assignments if assignment.user_id is not None}
    team_ids = {assignment.team_id for assignment in assignments if assignment.team_id is not None}
    if team_ids:
        conflicts.update(
            row.user_id
            for row in db.query(models.TeamMember.user_id).filter(
                models.TeamMember.organisation_id == organisation_id,
                models.TeamMember.team_id.in_(team_ids),
            )
        )
    return conflicts


def assignment_context(
    db: Session,
    organisation_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_patrol_id: int | None = None,
) -> dict[int, dict]:
    now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
    patrol_query = db.query(models.Patrol).filter(
        models.Patrol.organisation_id == organisation_id,
        models.Patrol.is_deleted.is_(False),
        models.Patrol.start_time.is_not(None),
        models.Patrol.end_time.is_not(None),
        models.Patrol.start_time < end_time,
        models.Patrol.end_time > start_time,
    )
    if exclude_patrol_id is not None:
        patrol_query = patrol_query.filter(models.Patrol.id != exclude_patrol_id)
    patrols = patrol_query.all()
    if not patrols:
        return {}
    assignments = db.query(models.PatrolAssignment).filter(
        models.PatrolAssignment.organisation_id == organisation_id,
        models.PatrolAssignment.patrol_id.in_([patrol.id for patrol in patrols]),
    ).all()
    patrol_by_id = {patrol.id: patrol for patrol in patrols}
    context = {}
    for assignment in assignments:
        patrol = patrol_by_id[assignment.patrol_id]
        member_ids = (
            {assignment.user_id}
            if assignment.user_id is not None
            else team_member_ids(db, assignment.team_id, organisation_id)
        )
        patrol_start = (
            patrol.start_time.replace(tzinfo=timezone.utc)
            if patrol.start_time.tzinfo is None
            else patrol.start_time
        )
        patrol_end = (
            patrol.end_time.replace(tzinfo=timezone.utc)
            if patrol.end_time.tzinfo is None
            else patrol.end_time
        )
        comparison_now = (
            now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now
        )
        currently_deployed = patrol_start <= comparison_now <= patrol_end
        for user_id in member_ids:
            if (
                context.get(user_id, {}).get('availability_state') == 'currently_deployed'
                and not currently_deployed
            ):
                continue
            context[user_id] = {
                'availability_state': (
                    'currently_deployed' if currently_deployed else 'scheduled'
                ),
                'reason': (
                    f'Currently deployed on {patrol.name}'
                    if currently_deployed
                    else f'Scheduled on {patrol.name} during this time'
                ),
                'active_deployment': patrol.name if currently_deployed else None,
            }
    return context


def scheduled_workloads(db: Session, organisation_id: int) -> tuple[dict[int, int], dict[int, int]]:
    now = datetime.now(timezone.utc)
    assignments = (
        db.query(models.PatrolAssignment)
        .join(models.Patrol, models.Patrol.id == models.PatrolAssignment.patrol_id)
        .filter(
            models.PatrolAssignment.organisation_id == organisation_id,
            models.Patrol.organisation_id == organisation_id,
            models.Patrol.is_deleted.is_(False),
            models.Patrol.end_time.is_not(None),
            models.Patrol.end_time >= now,
        )
        .all()
    )
    user_workloads: dict[int, int] = {}
    team_workloads: dict[int, int] = {}
    for assignment in assignments:
        if assignment.user_id is not None:
            user_workloads[assignment.user_id] = user_workloads.get(assignment.user_id, 0) + 1
        if assignment.team_id is not None:
            team_workloads[assignment.team_id] = team_workloads.get(assignment.team_id, 0) + 1
            for user_id in team_member_ids(db, assignment.team_id, organisation_id):
                user_workloads[user_id] = user_workloads.get(user_id, 0) + 1
    return user_workloads, team_workloads


def validate_schedule(start_time: datetime | None, end_time: datetime | None):
    if start_time is None or end_time is None:
        raise HTTPException(status_code=422, detail='Start and end times are required')
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail='End time must be after start time')


def resolve_assignment_users(
    db: Session,
    organisation_id: int,
    officer_ids: list[int],
    team_ids: list[int],
) -> tuple[list[models.User], list[models.Team], set[int]]:
    if len(set(officer_ids)) != len(officer_ids) or len(set(team_ids)) != len(team_ids):
        raise HTTPException(status_code=422, detail='Duplicate assignments are not allowed')

    users = db.query(models.User).filter(
        models.User.organisation_id == organisation_id,
        models.User.id.in_(officer_ids or [-1]),
        models.User.role.in_(OPERATIONAL_ROLES),
        models.User.is_active.is_(True),
        models.User.is_deleted.is_(False),
    ).all()
    if len(users) != len(officer_ids):
        raise HTTPException(status_code=422, detail='One or more selected officers are unavailable')

    teams = db.query(models.Team).filter(
        models.Team.organisation_id == organisation_id,
        models.Team.id.in_(team_ids or [-1]),
        models.Team.status == 'active',
        models.Team.is_deleted.is_(False),
    ).all()
    if len(teams) != len(team_ids):
        raise HTTPException(status_code=422, detail='One or more selected teams are unavailable')

    selected_user_ids = set(officer_ids)
    for team in teams:
        members = team_member_ids(db, team.id, organisation_id)
        if not members:
            raise HTTPException(status_code=422, detail=f'Team {team.name} has no active members')
        duplicate = selected_user_ids.intersection(members)
        if duplicate:
            raise HTTPException(
                status_code=422,
                detail=f'An officer from Team {team.name} was also selected individually',
            )
        selected_user_ids.update(members)
    return users, teams, selected_user_ids


def replace_patrol_assignments(
    db: Session,
    patrol: models.Patrol,
    officer_ids: list[int],
    team_ids: list[int],
    actor_user_id: int,
):
    if patrol.lifecycle_status in {'completed', 'missed', 'cancelled', 'archived'}:
        from ..domain.errors import ImmutableRecord
        raise ImmutableRecord('patrol_occurrence', patrol.lifecycle_status)
    # Deterministic order: patrol root, teams, users, canonical employees,
    # then existing assignment rows. This prevents caller-order deadlocks.
    db.query(models.Patrol.id).filter(
        models.Patrol.id == patrol.id,
        models.Patrol.organisation_id == patrol.organisation_id,
    ).with_for_update().all()
    db.query(models.User.id).filter(
        models.User.organisation_id == patrol.organisation_id,
        models.User.id.in_(sorted(set(officer_ids)) or [-1]),
    ).order_by(models.User.id).with_for_update().all()
    db.query(models.Team.id).filter(
        models.Team.organisation_id == patrol.organisation_id,
        models.Team.id.in_(sorted(set(team_ids)) or [-1]),
        models.Team.status == 'active', models.Team.is_deleted.is_(False),
    ).order_by(models.Team.id).with_for_update().all()
    users, teams, selected_user_ids = resolve_assignment_users(
        db, patrol.organisation_id, officer_ids, team_ids,
    )
    db.query(models.User.id).filter(
        models.User.organisation_id == patrol.organisation_id,
        models.User.id.in_(sorted(selected_user_ids) or [-1]),
    ).order_by(models.User.id).with_for_update().all()
    employees = db.query(models.Employee).filter(
        models.Employee.organisation_id == patrol.organisation_id,
        models.Employee.user_id.in_(sorted(selected_user_ids) or [-1]),
    ).order_by(models.Employee.id).with_for_update().all()
    inactive_employee_users = {
        employee.user_id for employee in employees
        if employee.status != 'active' or employee.is_deleted
    }
    if inactive_employee_users:
        from ..domain.errors import DomainError, DomainErrorCode
        raise DomainError(
            DomainErrorCode.ARCHIVED_DEPENDENCY,
            'An assigned employee is inactive or archived.',
        )
    conflicts = conflicting_user_ids(
        db,
        patrol.organisation_id,
        patrol.start_time,
        patrol.end_time,
        exclude_patrol_id=patrol.id,
    )
    conflicting_selected = conflicts.intersection(selected_user_ids)
    if conflicting_selected:
        names = [
            user.full_name or user.staff_identifier
            for user in operational_users(db, patrol.organisation_id)
            if user.id in conflicting_selected
        ]
        from ..domain.errors import DomainError, DomainErrorCode
        raise DomainError(
            DomainErrorCode.DUPLICATE_ASSIGNMENT,
            f"Assignment conflict for: {', '.join(names)}",
        )
    if len(selected_user_ids) < patrol.required_officers:
        raise HTTPException(
            status_code=422,
            detail=(
                f'Patrol requires {patrol.required_officers} officers but '
                f'only {len(selected_user_ids)} were assigned'
            ),
        )

    existing_assignments = db.query(models.PatrolAssignment).filter(
        models.PatrolAssignment.patrol_id == patrol.id,
        models.PatrolAssignment.organisation_id == patrol.organisation_id,
    ).order_by(models.PatrolAssignment.id).with_for_update().all()
    for assignment in existing_assignments:
        db.delete(assignment)
    db.flush()
    for user in users:
        employee = db.query(models.Employee).filter(
            models.Employee.organisation_id == patrol.organisation_id,
            models.Employee.user_id == user.id,
        ).one_or_none()
        db.add(models.PatrolAssignment(
            patrol_id=patrol.id,
            user_id=user.id,
            employee_id=employee.id if employee else None,
            employee_reference_source='canonical_user_mapping' if employee else 'legacy_user_only',
            organisation_id=patrol.organisation_id,
            created_by=actor_user_id,
        ))
    for team in teams:
        db.add(models.PatrolAssignment(
            patrol_id=patrol.id,
            team_id=team.id,
            organisation_id=patrol.organisation_id,
            created_by=actor_user_id,
        ))


def user_summary(user: models.User):
    return {
        'id': user.id,
        'full_name': user.full_name,
        'staff_identifier': user.staff_identifier,
        'role': user.role,
    }


def team_payload(
    db: Session,
    team: models.Team,
    active_patrols: list[str] | None = None,
    workload_count: int = 0,
):
    members = (
        db.query(models.User)
        .join(models.TeamMember, models.TeamMember.user_id == models.User.id)
        .filter(
            models.TeamMember.team_id == team.id,
            models.TeamMember.organisation_id == team.organisation_id,
            models.User.is_active.is_(True),
            models.User.is_deleted.is_(False),
        )
        .order_by(models.User.full_name.asc(), models.User.id.asc())
        .all()
    )
    patrol_names = active_patrols or []
    return {
        'id': team.id,
        'name': team.name,
        'leader_user_id': team.leader_user_id,
        'notes': team.notes,
        'status': team.status,
        'members': [user_summary(user) for user in members],
        'availability': 'deployed' if patrol_names else 'available',
        'active_patrols': patrol_names,
        'workload_count': workload_count,
    }
