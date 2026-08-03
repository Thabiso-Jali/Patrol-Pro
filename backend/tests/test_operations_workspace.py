import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import event

from backend.app import models
from backend.app.database import SessionLocal, engine
from backend.app.main import app
from backend.app.services.operations_workspace import build_operations_workspace
from backend.app.services import operations_workspace
from backend.tests.invitation_test_utils import post_development_invitation


client = TestClient(app)


def register_owner(prefix='workspace'):
    unique = uuid.uuid4().hex
    email = f'{prefix}+{unique}@example.com'
    password = 'TestPass123!'
    response = client.post('/api/v1/auth/register', json={
        'email': email,
        'full_name': 'Workspace Owner',
        'password': password,
        'organisation_name': f'Workspace Security {unique}',
    })
    assert response.status_code == 200
    token = client.post('/api/v1/auth/token', data={
        'username': email, 'password': password,
    }).json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    organisation_id = client.get('/api/v1/auth/me', headers=headers).json()['company']['id']
    return headers, organisation_id


def invite(headers, name, role='employee'):
    email = f'{name.lower().replace(" ", "-")}+{uuid.uuid4().hex}@example.com'
    invitation = post_development_invitation(client, headers=headers, json={
        'email': email, 'full_name': name, 'role': role,
    })
    assert invitation.status_code == 201
    accepted = client.post('/api/v1/invitations/accept', json={
        'token': invitation.json()['invitation_token'],
        'password': 'AssignedPass123!',
    })
    assert accepted.status_code == 201
    return accepted.json(), email


def auth_headers(email):
    token = client.post('/api/v1/auth/token', data={
        'username': email, 'password': 'AssignedPass123!',
    }).json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_workspace_requires_authentication_and_management_permission():
    assert client.get('/api/v1/operations/workspace').status_code == 401
    owner_headers, _ = register_owner('workspace-denied')
    _, officer_email = invite(owner_headers, 'Field Officer')
    assert client.get(
        '/api/v1/operations/workspace', headers=auth_headers(officer_email),
    ).status_code == 403


def test_empty_workspace_is_truthful_and_stable():
    headers, _ = register_owner('workspace-empty')
    response = client.get('/api/v1/operations/workspace', headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload['metrics'] == {
        'active_workforce': 0,
        'available_workforce': 0,
        'deployed_workforce': 0,
        'inactive_workforce': 0,
        'workforce_without_team': 0,
        'active_teams': 0,
        'active_patrols': 0,
    }
    assert payload['staff'] == []
    assert payload['teams'] == []
    assert 'does not represent presence' in payload['availability_definition']


def test_workspace_derives_staff_team_and_current_deployment_per_tenant():
    headers, organisation_id = register_owner('workspace-live')
    other_headers, _ = register_owner('workspace-other')
    deployed, _ = invite(headers, 'Deployed Officer')
    available, _ = invite(headers, 'Available Officer')
    inactive, _ = invite(headers, 'Inactive Officer')
    invite(other_headers, 'Other Tenant Officer')

    team = client.post('/api/v1/teams', headers=headers, json={
        'name': 'Team Alpha',
        'leader_user_id': deployed['id'],
        'member_user_ids': [deployed['id'], inactive['id']],
        'status': 'active',
    })
    assert team.status_code == 201
    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.id == inactive['id']).one()
        user.is_active = False
        db.commit()

    now = datetime.now(timezone.utc)
    patrol = client.post('/api/v1/patrols/', headers=headers, json={
        'name': 'Current Team Patrol',
        'start_time': (now - timedelta(minutes=5)).isoformat(),
        'end_time': (now + timedelta(hours=1)).isoformat(),
        'required_officers': 1,
        'officer_ids': [deployed['id']],
    })
    assert patrol.status_code == 200
    with SessionLocal() as db:
        db.add(models.PatrolAssignment(
            patrol_id=patrol.json()['id'],
            team_id=team.json()['id'],
            organisation_id=organisation_id,
        ))
        db.commit()

    payload = client.get('/api/v1/operations/workspace', headers=headers).json()
    assert payload['metrics'] == {
        'active_workforce': 2,
        'available_workforce': 1,
        'deployed_workforce': 1,
        'inactive_workforce': 1,
        'workforce_without_team': 1,
        'active_teams': 1,
        'active_patrols': 1,
    }
    assert {person['full_name'] for person in payload['staff']} == {
        'Deployed Officer', 'Available Officer', 'Inactive Officer',
    }
    deployed_row = next(row for row in payload['staff'] if row['id'] == deployed['id'])
    assert deployed_row['availability_status'] == 'deployed'
    assert deployed_row['team_name'] == 'Team Alpha'
    team_row = payload['teams'][0]
    assert team_row['active_member_count'] == 1
    assert team_row['inactive_member_count'] == 1
    assert team_row['deployed_member_count'] == 1
    assert team_row['current_patrols'] == ['Current Team Patrol']
    assert 'Other Tenant Officer' not in str(payload)

    other_payload = client.get('/api/v1/operations/workspace', headers=other_headers).json()
    assert {row['full_name'] for row in other_payload['staff']} == {'Other Tenant Officer'}
    assert organisation_id != client.get('/api/v1/auth/me', headers=other_headers).json()['company']['id']


def test_workspace_projection_has_bounded_query_count_and_does_not_mutate():
    headers, organisation_id = register_owner('workspace-query-count')
    invite(headers, 'Query Officer')
    statements = []

    def record_statement(*args):
        statements.append(args[2])

    with SessionLocal() as db:
        before = (len(db.new), len(db.dirty), len(db.deleted))
        event.listen(engine, 'before_cursor_execute', record_statement)
        try:
            payload = build_operations_workspace(db, organisation_id)
        finally:
            event.remove(engine, 'before_cursor_execute', record_statement)
        after = (len(db.new), len(db.dirty), len(db.deleted))

    assert payload['metrics']['active_workforce'] == 1
    assert len(statements) <= 5
    assert before == after == (0, 0, 0)


def test_workspace_uses_one_injected_as_of_and_enforces_row_ceiling(monkeypatch):
    headers, organisation_id = register_owner('workspace-bounds')
    invite(headers, 'Bounded Officer')
    instant = datetime(2026, 8, 3, 12, 34, tzinfo=timezone.utc)
    with SessionLocal() as db:
        payload = build_operations_workspace(db, organisation_id, as_of=instant)
        assert payload['as_of'] == instant
        monkeypatch.setattr(operations_workspace, 'MAX_WORKFORCE_ROWS', 0)
        try:
            build_operations_workspace(db, organisation_id, as_of=instant)
        except HTTPException as exc:
            assert exc.status_code == 503
            assert 'safe workspace display limit' in exc.detail
        else:
            raise AssertionError('The projection did not enforce its workforce row ceiling')
