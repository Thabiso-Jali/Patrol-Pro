from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from .... import models, schemas
from ....database import SessionLocal
from ....domain.registry import DomainObjectType
from ....permissions import Permission
from ....security import require_permissions
from ....services.audit import log_audit_event
from ....services.domain_registry import register_domain_object
from ....services.transactions import transactional_session
from ....services.concurrency import assert_expected_version, lock_tenant_record, parse_expected_version
from ....services.teams import archive_team as archive_team_command
from ....services.staffing import (
    assignment_context,
    operational_users,
    scheduled_workloads,
    team_member_ids,
    team_payload,
    user_summary,
    validate_schedule,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_scoped_team(db: Session, team_id: int, organisation_id: int):
    return db.query(models.Team).filter(
        models.Team.id == team_id,
        models.Team.organisation_id == organisation_id,
        models.Team.is_deleted.is_(False),
    ).first()


def validate_members(
    db: Session,
    organisation_id: int,
    member_user_ids: list[int],
    leader_user_id: int | None,
    team_id: int | None = None,
):
    if len(member_user_ids) != len(set(member_user_ids)):
        raise HTTPException(status_code=422, detail='An officer cannot be added twice')
    users = db.query(models.User).filter(
        models.User.organisation_id == organisation_id,
        models.User.id.in_(member_user_ids or [-1]),
        models.User.role.in_(['officer', 'employee']),
        models.User.is_active.is_(True),
        models.User.is_deleted.is_(False),
    ).all()
    if len(users) != len(member_user_ids):
        raise HTTPException(status_code=422, detail='One or more officers are inactive or invalid')
    if leader_user_id is not None and leader_user_id not in member_user_ids:
        raise HTTPException(status_code=422, detail='Team leader must be a team member')
    existing = db.query(models.TeamMember).filter(
        models.TeamMember.organisation_id == organisation_id,
        models.TeamMember.user_id.in_(member_user_ids or [-1]),
    )
    if team_id is not None:
        existing = existing.filter(models.TeamMember.team_id != team_id)
    if existing.first():
        raise HTTPException(status_code=409, detail='An officer already belongs to another team')
    return users


def replace_members(
    db: Session,
    team: models.Team,
    member_user_ids: list[int],
    actor_user_id: int,
):
    existing_members = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team.id,
        models.TeamMember.organisation_id == team.organisation_id,
    ).all()
    for member in existing_members:
        db.delete(member)
    db.flush()
    for user_id in member_user_ids:
        employee = db.query(models.Employee).filter(
            models.Employee.organisation_id == team.organisation_id,
            models.Employee.user_id == user_id,
        ).one_or_none()
        db.add(models.TeamMember(
            team_id=team.id,
            user_id=user_id,
            employee_id=employee.id if employee else None,
            employee_reference_source='canonical_user_mapping' if employee else 'legacy_user_only',
            organisation_id=team.organisation_id,
            created_by=actor_user_id,
        ))


def active_patrol_names(db: Session, team_id: int, organisation_id: int):
    now = datetime.now(timezone.utc)
    return [
        row.name
        for row in (
            db.query(models.Patrol.name)
            .join(
                models.PatrolAssignment,
                models.PatrolAssignment.patrol_id == models.Patrol.id,
            )
            .filter(
                models.PatrolAssignment.team_id == team_id,
                models.PatrolAssignment.organisation_id == organisation_id,
                models.Patrol.organisation_id == organisation_id,
                models.Patrol.is_deleted.is_(False),
                models.Patrol.start_time <= now,
                models.Patrol.end_time >= now,
            )
        )
    ]


@router.get('', response_model=list[schemas.Team])
def list_teams(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_permissions(Permission.TEAMS_VIEW, Permission.USERS_VIEW)
    ),
):
    teams = db.query(models.Team).filter(
        models.Team.organisation_id == current_user.organisation_id,
        models.Team.is_deleted.is_(False),
    ).order_by(models.Team.name.asc()).all()
    return [
        team_payload(
            db,
            team,
            active_patrol_names(db, team.id, current_user.organisation_id),
        )
        for team in teams
    ]


@router.get('/mine', response_model=schemas.Team | None)
def my_team(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permissions(Permission.TEAMS_VIEW)),
):
    team = (
        db.query(models.Team)
        .join(models.TeamMember, models.TeamMember.team_id == models.Team.id)
        .filter(
            models.TeamMember.user_id == current_user.id,
            models.TeamMember.organisation_id == current_user.organisation_id,
            models.Team.organisation_id == current_user.organisation_id,
            models.Team.is_deleted.is_(False),
        )
        .first()
    )
    if not team:
        return None
    return team_payload(
        db,
        team,
        active_patrol_names(db, team.id, current_user.organisation_id),
    )


@router.get('/availability', response_model=schemas.AvailabilityResult)
def availability(
    start_time: datetime = Query(),
    end_time: datetime = Query(),
    exclude_patrol_id: int | None = Query(default=None, ge=1),
    required_officers: int = Query(default=1, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permissions(Permission.PATROLS_MANAGE)),
):
    validate_schedule(start_time, end_time)
    conflict_details = assignment_context(
        db,
        current_user.organisation_id,
        start_time,
        end_time,
        exclude_patrol_id,
    )
    conflicts = set(conflict_details)
    user_workloads, team_workloads = scheduled_workloads(
        db, current_user.organisation_id,
    )
    users = operational_users(db, current_user.organisation_id)
    available_users = [user for user in users if user.id not in conflicts]
    unavailable_users = [user for user in users if user.id in conflicts]
    teams = db.query(models.Team).filter(
        models.Team.organisation_id == current_user.organisation_id,
        models.Team.status == 'active',
        models.Team.is_deleted.is_(False),
    ).order_by(models.Team.name.asc()).all()
    available_teams = []
    unavailable_teams = []
    for team in teams:
        member_ids = team_member_ids(db, team.id, current_user.organisation_id)
        payload = team_payload(
            db, team, workload_count=team_workloads.get(team.id, 0),
        )
        if member_ids and not member_ids.intersection(conflicts):
            available_teams.append(payload)
        else:
            deployment_names = sorted({
                conflict_details[user_id]['active_deployment']
                for user_id in member_ids.intersection(conflicts)
                if conflict_details[user_id].get('active_deployment')
            })
            payload['availability'] = (
                'currently_deployed' if deployment_names else 'scheduled'
            )
            payload['active_patrols'] = deployment_names
            if not member_ids:
                payload['reason'] = 'Team has no active members'
            else:
                conflicting_names = [
                    user.full_name or user.staff_identifier
                    for user in users
                    if user.id in member_ids.intersection(conflicts)
                ]
                payload['reason'] = f"Unavailable member: {', '.join(conflicting_names)}"
            unavailable_teams.append(payload)
    user_team_rows = db.query(
        models.TeamMember.user_id,
        models.Team.id,
        models.Team.name,
    ).join(models.Team, models.Team.id == models.TeamMember.team_id).filter(
        models.TeamMember.organisation_id == current_user.organisation_id,
        models.Team.organisation_id == current_user.organisation_id,
        models.Team.is_deleted.is_(False),
    ).all()
    team_by_user = {
        user_id: {'team_id': team_id, 'team_name': team_name}
        for user_id, team_id, team_name in user_team_rows
    }

    def officer_payload(user, available):
        team = team_by_user.get(user.id, {})
        context = conflict_details.get(user.id, {})
        return {
            **user_summary(user),
            **team,
            'availability_state': context.get('availability_state', 'available'),
            'reason': context.get('reason'),
            'active_deployment': context.get('active_deployment'),
            'workload_count': user_workloads.get(user.id, 0),
        }

    ranked_teams = sorted(
        available_teams,
        key=lambda team: (
            0 if len(team['members']) == required_officers else 1,
            max(0, required_officers - len(team['members'])),
            team['workload_count'],
            max(0, len(team['members']) - required_officers),
            team['name'].lower(),
        ),
    )
    ranked_officers = sorted(
        available_users,
        key=lambda user: (
            user_workloads.get(user.id, 0),
            (user.full_name or user.staff_identifier).lower(),
        ),
    )
    recommendation = None
    if ranked_teams:
        recommended_team = ranked_teams[0]
        team_member_ids_selected = {
            member['id'] for member in recommended_team['members']
        }
        additional_needed = max(0, required_officers - len(team_member_ids_selected))
        extras = [
            user for user in ranked_officers if user.id not in team_member_ids_selected
        ][:additional_needed]
        covered = len(team_member_ids_selected) + len(extras)
        recommendation = {
            'team_ids': [recommended_team['id']],
            'officer_ids': [user.id for user in extras],
            'covered_officers': covered,
            'required_officers': required_officers,
            'explanation': (
                f"{recommended_team['name']} exactly matches the staffing requirement"
                if len(team_member_ids_selected) == required_officers
                else (
                    f"{recommended_team['name']} has the smallest staffing gap; "
                    f"{len(extras)} additional officer(s) recommended"
                )
            ),
        }
    elif ranked_officers:
        extras = ranked_officers[:required_officers]
        recommendation = {
            'team_ids': [],
            'officer_ids': [user.id for user in extras],
            'covered_officers': len(extras),
            'required_officers': required_officers,
            'explanation': 'Available officers with the lightest scheduled workload',
        }
    return {
        'available_officers': [officer_payload(user, True) for user in ranked_officers],
        'unavailable_officers': [officer_payload(user, False) for user in unavailable_users],
        'available_teams': available_teams,
        'unavailable_teams': unavailable_teams,
        'recommendation': recommendation,
    }


@router.post('', response_model=schemas.Team, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: schemas.TeamCreate,
    db: Session = Depends(transactional_session),
    current_user: models.User = Depends(require_permissions(Permission.USERS_MANAGE)),
):
    validate_members(
        db,
        current_user.organisation_id,
        payload.member_user_ids,
        payload.leader_user_id,
    )
    existing = db.query(models.Team).filter(
        models.Team.organisation_id == current_user.organisation_id,
        models.Team.name == payload.name.strip(),
        models.Team.is_deleted.is_(False),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail='A team with this name already exists')
    team = models.Team(
        name=payload.name.strip(),
        leader_user_id=payload.leader_user_id,
        notes=payload.notes,
        status=payload.status,
        organisation_id=current_user.organisation_id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(team)
    db.flush()
    register_domain_object(
        db, organisation_id=current_user.organisation_id,
        object_type=DomainObjectType.TEAM, object_id=team.id,
    )
    replace_members(db, team, payload.member_user_ids, current_user.id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        organisation_id=current_user.organisation_id,
        action='team.create',
        entity_type='team',
        entity_id=str(team.id),
    )
    return team_payload(db, team)


@router.put('/{team_id}', response_model=schemas.Team)
def update_team(
    team_id: int,
    payload: schemas.TeamCreate,
    db: Session = Depends(transactional_session),
    current_user: models.User = Depends(require_permissions(Permission.USERS_MANAGE)),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    team = get_scoped_team(db, team_id, current_user.organisation_id)
    if not team:
        raise HTTPException(status_code=404, detail='Team not found')
    team = lock_tenant_record(
        db, models.Team, record_id=team_id,
        organisation_id=current_user.organisation_id, relationship='Team',
    )
    assert_expected_version(team, parse_expected_version(if_match))
    current_members = team_member_ids(db, team.id, current_user.organisation_id)
    if current_members != set(payload.member_user_ids) and active_patrol_names(
        db, team.id, current_user.organisation_id,
    ):
        raise HTTPException(
            status_code=409,
            detail='Team membership cannot change during an active patrol',
        )
    validate_members(
        db,
        current_user.organisation_id,
        payload.member_user_ids,
        payload.leader_user_id,
        team_id=team.id,
    )
    duplicate = db.query(models.Team).filter(
        models.Team.organisation_id == current_user.organisation_id,
        models.Team.name == payload.name.strip(),
        models.Team.id != team.id,
        models.Team.is_deleted.is_(False),
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail='A team with this name already exists')
    team.name = payload.name.strip()
    team.leader_user_id = payload.leader_user_id
    team.notes = payload.notes
    team.status = payload.status
    team.updated_by = current_user.id
    team.record_version += 1
    replace_members(db, team, payload.member_user_ids, current_user.id)
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        organisation_id=current_user.organisation_id,
        action='team.update',
        entity_type='team',
        entity_id=str(team.id),
    )
    return team_payload(db, team)


@router.delete('/{team_id}', status_code=status.HTTP_204_NO_CONTENT)
def archive_team(
    team_id: int,
    db: Session = Depends(transactional_session),
    current_user: models.User = Depends(require_permissions(Permission.USERS_MANAGE)),
    if_match: str | None = Header(default=None, alias='If-Match'),
):
    team = get_scoped_team(db, team_id, current_user.organisation_id)
    if not team:
        raise HTTPException(status_code=404, detail='Team not found')
    team = lock_tenant_record(
        db, models.Team, record_id=team_id,
        organisation_id=current_user.organisation_id, relationship='Team',
    )
    assert_expected_version(team, parse_expected_version(if_match))
    if active_patrol_names(db, team.id, current_user.organisation_id):
        raise HTTPException(status_code=409, detail='An active patrol is using this team')
    archive_team_command(
        db, organisation_id=current_user.organisation_id, team_id=team.id,
        actor_user_id=current_user.id, expected_version=parse_expected_version(if_match),
    )
    log_audit_event(
        db,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        organisation_id=current_user.organisation_id,
        action='team.archive',
        entity_type='team',
        entity_id=str(team.id),
    )
    return None
