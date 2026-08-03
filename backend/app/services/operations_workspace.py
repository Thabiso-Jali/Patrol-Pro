from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models
from .staffing import OPERATIONAL_ROLES


ACTIVE_PATROL_STATES = {'scheduled', 'in_progress'}
MAX_WORKFORCE_ROWS = 2_000
MAX_TEAM_ROWS = 500
MAX_CURRENT_PATROL_ROWS = 1_000
MAX_ASSIGNMENT_ROWS = 10_000
AVAILABILITY_DEFINITION = (
    'Assignment availability at the as-of time: active account with no '
    'overlapping current patrol assignment. It does not represent presence, '
    'shift, leave, fatigue, qualification or licence status.'
)
METRIC_DEFINITIONS = {
    'active_workforce': 'Non-deleted operational workforce accounts that are active.',
    'available_workforce': 'Active workforce with no current patrol assignment at as_of.',
    'deployed_workforce': 'Active workforce assigned directly or through a Team to a patrol active at as_of.',
    'inactive_workforce': 'Non-deleted operational workforce accounts that are inactive.',
    'workforce_without_team': 'Active workforce with no current Team membership.',
    'active_teams': 'Non-deleted Teams whose canonical status is active.',
    'active_patrols': 'Non-deleted scheduled/in-progress patrols whose time window contains as_of.',
}


def _bounded(rows, limit: int, label: str):
    if len(rows) > limit:
        raise HTTPException(
            status_code=503,
            detail=f'{label} exceeds the safe workspace display limit.',
        )
    return rows


def build_operations_workspace(
    db: Session,
    organisation_id: int,
    *,
    as_of: datetime | None = None,
):
    """Build one bounded, tenant-scoped compatibility projection for operations."""
    instant = as_of or datetime.now(timezone.utc)

    users = (
        db.query(models.User)
        .filter(
            models.User.organisation_id == organisation_id,
            models.User.role.in_(OPERATIONAL_ROLES),
            models.User.is_deleted.is_(False),
        )
        .order_by(models.User.full_name.asc(), models.User.id.asc())
        .limit(MAX_WORKFORCE_ROWS + 1)
        .all()
    )
    users = _bounded(users, MAX_WORKFORCE_ROWS, 'Operational workforce')
    teams = (
        db.query(models.Team)
        .filter(
            models.Team.organisation_id == organisation_id,
            models.Team.is_deleted.is_(False),
        )
        .order_by(models.Team.name.asc(), models.Team.id.asc())
        .limit(MAX_TEAM_ROWS + 1)
        .all()
    )
    teams = _bounded(teams, MAX_TEAM_ROWS, 'Teams')
    memberships = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.organisation_id == organisation_id)
        .limit(MAX_WORKFORCE_ROWS + 1)
        .all()
    )
    memberships = _bounded(memberships, MAX_WORKFORCE_ROWS, 'Team memberships')
    patrols = (
        db.query(models.Patrol)
        .filter(
            models.Patrol.organisation_id == organisation_id,
            models.Patrol.is_deleted.is_(False),
            models.Patrol.lifecycle_status.in_(ACTIVE_PATROL_STATES),
            models.Patrol.start_time.is_not(None),
            models.Patrol.end_time.is_not(None),
            models.Patrol.start_time <= instant,
            models.Patrol.end_time > instant,
        )
        .order_by(models.Patrol.start_time.asc(), models.Patrol.id.asc())
        .limit(MAX_CURRENT_PATROL_ROWS + 1)
        .all()
    )
    patrols = _bounded(patrols, MAX_CURRENT_PATROL_ROWS, 'Current patrols')
    assignments = []
    if patrols:
        assignments = (
            db.query(models.PatrolAssignment)
            .filter(
                models.PatrolAssignment.organisation_id == organisation_id,
                models.PatrolAssignment.patrol_id.in_([patrol.id for patrol in patrols]),
            )
            .limit(MAX_ASSIGNMENT_ROWS + 1)
            .all()
        )
        assignments = _bounded(
            assignments, MAX_ASSIGNMENT_ROWS, 'Current patrol assignments',
        )

    user_by_id = {user.id: user for user in users}
    team_by_id = {team.id: team for team in teams}
    membership_by_user = {}
    member_ids_by_team = defaultdict(set)
    for membership in memberships:
        if membership.user_id not in user_by_id or membership.team_id not in team_by_id:
            continue
        membership_by_user[membership.user_id] = membership.team_id
        member_ids_by_team[membership.team_id].add(membership.user_id)

    patrol_by_id = {patrol.id: patrol for patrol in patrols}
    patrol_names_by_user = defaultdict(set)
    patrol_names_by_team = defaultdict(set)
    for assignment in assignments:
        patrol = patrol_by_id.get(assignment.patrol_id)
        if patrol is None:
            continue
        if assignment.user_id in user_by_id:
            patrol_names_by_user[assignment.user_id].add(patrol.name)
        if assignment.team_id in team_by_id:
            patrol_names_by_team[assignment.team_id].add(patrol.name)
            for user_id in member_ids_by_team[assignment.team_id]:
                patrol_names_by_user[user_id].add(patrol.name)

    staff = []
    for user in users:
        team_id = membership_by_user.get(user.id)
        current_patrols = sorted(patrol_names_by_user[user.id])
        is_active = bool(user.is_active)
        staff.append({
            'id': user.id,
            'full_name': user.full_name,
            'staff_identifier': user.staff_identifier,
            'role': user.role,
            'account_status': 'active' if is_active else 'inactive',
            'availability_status': (
                'inactive' if not is_active else
                'deployed' if current_patrols else
                'available'
            ),
            'team_id': team_id,
            'team_name': team_by_id[team_id].name if team_id in team_by_id else None,
            'current_patrols': current_patrols,
        })

    team_rows = []
    for team in teams:
        team_members = [
            user_by_id[user_id]
            for user_id in member_ids_by_team[team.id]
            if user_id in user_by_id
        ]
        active_members = [member for member in team_members if member.is_active]
        deployed_ids = {
            member.id for member in active_members if patrol_names_by_user[member.id]
        }
        current_patrols = set(patrol_names_by_team[team.id])
        for member in team_members:
            current_patrols.update(patrol_names_by_user[member.id])
        attention = []
        if team.status == 'active' and not active_members:
            attention.append('No active members')
        if team.status == 'active' and team.leader_user_id is None:
            attention.append('No leader assigned')
        leader = user_by_id.get(team.leader_user_id)
        if team.status == 'active' and leader is not None and not leader.is_active:
            attention.append('Team leader is inactive')
        team_rows.append({
            'id': team.id,
            'name': team.name,
            'status': team.status,
            'leader_user_id': team.leader_user_id,
            'leader_name': leader.full_name if leader else None,
            'active_member_count': len(active_members),
            'inactive_member_count': len(team_members) - len(active_members),
            'available_member_count': len(active_members) - len(deployed_ids),
            'deployed_member_count': len(deployed_ids),
            'current_patrols': sorted(current_patrols),
            'attention': attention,
        })

    active_staff = [row for row in staff if row['account_status'] == 'active']
    return {
        'as_of': instant,
        'availability_definition': AVAILABILITY_DEFINITION,
        'metric_definitions': METRIC_DEFINITIONS,
        'metrics': {
            'active_workforce': len(active_staff),
            'available_workforce': sum(
                row['availability_status'] == 'available' for row in active_staff
            ),
            'deployed_workforce': sum(
                row['availability_status'] == 'deployed' for row in active_staff
            ),
            'inactive_workforce': len(staff) - len(active_staff),
            'workforce_without_team': sum(
                row['team_id'] is None for row in active_staff
            ),
            'active_teams': sum(team.status == 'active' for team in teams),
            'active_patrols': len(patrols),
        },
        'staff': staff,
        'teams': team_rows,
    }
