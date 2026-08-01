import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.database import engine
from backend.app.main import app
from backend.tests.invitation_test_utils import post_development_invitation

client = TestClient(app)


def register_owner():
    unique = uuid.uuid4().hex
    email = f'owner+{unique}@example.com'
    password = 'StrongPass123!'
    response = client.post('/api/v1/auth/register', json={
        'company_name': f'Team Security {unique}',
        'business_email': email,
        'owner_name': 'Team Owner',
        'owner_email': email,
        'password': password,
    })
    assert response.status_code == 200
    token = client.post('/api/v1/auth/token', data={'username': email, 'password': password})
    return response.json(), {'Authorization': f"Bearer {token.json()['access_token']}"}


def invite_and_accept(headers, name):
    email = f'{name.lower().replace(" ", "-")}+{uuid.uuid4().hex}@example.com'
    invitation = post_development_invitation(client, headers=headers, json={
        'full_name': name,
        'email': email,
        'role': 'employee',
    })
    assert invitation.status_code == 201
    accepted = client.post('/api/v1/invitations/accept', json={
        'token': invitation.json()['invitation_token'],
        'password': 'EmployeePass123!',
    })
    assert accepted.status_code == 201
    token = client.post('/api/v1/auth/token', data={
        'username': email,
        'password': 'EmployeePass123!',
    })
    return accepted.json(), {'Authorization': f"Bearer {token.json()['access_token']}"}


def test_team_members_can_see_safe_coworker_identification():
    _, owner_headers = register_owner()
    first, first_headers = invite_and_accept(owner_headers, 'Officer Smith')
    second, _ = invite_and_accept(owner_headers, 'Officer Jones')

    team = client.post('/api/v1/teams', headers=owner_headers, json={
        'name': 'Team Alpha',
        'leader_user_id': first['id'],
        'member_user_ids': [first['id'], second['id']],
        'status': 'active',
        'notes': 'Primary response team',
    })
    assert team.status_code == 201

    mine = client.get('/api/v1/teams/mine', headers=first_headers)
    assert mine.status_code == 200
    assert mine.json()['name'] == 'Team Alpha'
    assert {member['staff_identifier'] for member in mine.json()['members']} == {
        first['staff_identifier'],
        second['staff_identifier'],
    }
    assert all('email' not in member for member in mine.json()['members'])


def test_overlapping_team_and_officer_assignments_are_rejected():
    _, owner_headers = register_owner()
    first, _ = invite_and_accept(owner_headers, 'Available Officer')
    second, _ = invite_and_accept(owner_headers, 'Team Officer')
    team = client.post('/api/v1/teams', headers=owner_headers, json={
        'name': 'Team Bravo',
        'leader_user_id': second['id'],
        'member_user_ids': [second['id']],
        'status': 'active',
    }).json()
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(hours=2)

    created = client.post('/api/v1/patrols/', headers=owner_headers, json={
        'name': 'Scheduled team patrol',
        'start_time': start.isoformat(),
        'end_time': end.isoformat(),
        'required_officers': 1,
        'team_ids': [team['id']],
    })
    assert created.status_code == 200
    assert created.json()['team_ids'] == [team['id']]

    availability = client.get('/api/v1/teams/availability', headers=owner_headers, params={
        'start_time': start.isoformat(),
        'end_time': end.isoformat(),
    })
    assert availability.status_code == 200
    assert [row['id'] for row in availability.json()['available_officers']] == [first['id']]
    assert [row['id'] for row in availability.json()['unavailable_officers']] == [second['id']]

    conflict = client.post('/api/v1/patrols/', headers=owner_headers, json={
        'name': 'Conflicting individual patrol',
        'start_time': (start + timedelta(minutes=30)).isoformat(),
        'end_time': (end + timedelta(minutes=30)).isoformat(),
        'required_officers': 1,
        'officer_ids': [second['id']],
    })
    assert conflict.status_code == 409


def test_team_validation_prevents_leader_and_membership_errors():
    _, owner_headers = register_owner()
    first, _ = invite_and_accept(owner_headers, 'First Officer')
    second, _ = invite_and_accept(owner_headers, 'Second Officer')

    invalid_leader = client.post('/api/v1/teams', headers=owner_headers, json={
        'name': 'Invalid Leader',
        'leader_user_id': second['id'],
        'member_user_ids': [first['id']],
    })
    assert invalid_leader.status_code == 422

    client.post('/api/v1/teams', headers=owner_headers, json={
        'name': 'First Team',
        'leader_user_id': first['id'],
        'member_user_ids': [first['id']],
    })
    duplicate_membership = client.post('/api/v1/teams', headers=owner_headers, json={
        'name': 'Second Team',
        'leader_user_id': first['id'],
        'member_user_ids': [first['id']],
    })
    assert duplicate_membership.status_code == 409


def test_exact_size_team_is_recommended_before_individuals():
    _, owner_headers = register_owner()
    first, _ = invite_and_accept(owner_headers, 'Exact One')
    second, _ = invite_and_accept(owner_headers, 'Exact Two')
    invite_and_accept(owner_headers, 'Unassigned Officer')
    team = client.post('/api/v1/teams', headers=owner_headers, json={
        'name': 'Exact Team',
        'leader_user_id': first['id'],
        'member_user_ids': [first['id'], second['id']],
        'status': 'active',
    }).json()
    start = datetime.now(timezone.utc) + timedelta(days=1)
    availability = client.get('/api/v1/teams/availability', headers=owner_headers, params={
        'start_time': start.isoformat(),
        'end_time': (start + timedelta(hours=2)).isoformat(),
        'required_officers': 2,
    })
    assert availability.status_code == 200
    recommendation = availability.json()['recommendation']
    assert recommendation['team_ids'] == [team['id']]
    assert recommendation['officer_ids'] == []
    assert recommendation['covered_officers'] == 2


def test_partial_team_uses_lightest_workload_officer():
    _, owner_headers = register_owner()
    member, _ = invite_and_accept(owner_headers, 'Partial Member')
    busy, _ = invite_and_accept(owner_headers, 'Busy Extra')
    light, _ = invite_and_accept(owner_headers, 'Light Extra')
    team = client.post('/api/v1/teams', headers=owner_headers, json={
        'name': 'Partial Team',
        'leader_user_id': member['id'],
        'member_user_ids': [member['id']],
        'status': 'active',
    }).json()
    workload_start = datetime.now(timezone.utc) + timedelta(days=3)
    workload = client.post('/api/v1/patrols/', headers=owner_headers, json={
        'name': 'Future workload',
        'start_time': workload_start.isoformat(),
        'end_time': (workload_start + timedelta(hours=1)).isoformat(),
        'required_officers': 1,
        'officer_ids': [busy['id']],
    })
    assert workload.status_code == 200

    start = datetime.now(timezone.utc) + timedelta(days=1)
    availability = client.get('/api/v1/teams/availability', headers=owner_headers, params={
        'start_time': start.isoformat(),
        'end_time': (start + timedelta(hours=2)).isoformat(),
        'required_officers': 2,
    })
    assert availability.status_code == 200
    recommendation = availability.json()['recommendation']
    assert recommendation['team_ids'] == [team['id']]
    assert recommendation['officer_ids'] == [light['id']]
    workloads = {
        officer['id']: officer['workload_count']
        for officer in availability.json()['available_officers']
    }
    assert workloads[busy['id']] > workloads[light['id']]


def test_inactive_officer_and_team_are_excluded():
    _, owner_headers = register_owner()
    active, _ = invite_and_accept(owner_headers, 'Active Officer')
    inactive, _ = invite_and_accept(owner_headers, 'Inactive Officer')
    team = client.post('/api/v1/teams', headers=owner_headers, json={
        'name': 'Inactive Team',
        'leader_user_id': active['id'],
        'member_user_ids': [active['id']],
        'status': 'active',
    }).json()
    client.put(f"/api/v1/teams/{team['id']}", headers=owner_headers, json={
        'name': 'Inactive Team',
        'leader_user_id': active['id'],
        'member_user_ids': [active['id']],
        'status': 'inactive',
    })

    from backend.app import models
    from backend.app.database import SessionLocal
    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.id == inactive['id']).one()
        user.is_active = False
        db.commit()

    start = datetime.now(timezone.utc) + timedelta(days=1)
    availability = client.get('/api/v1/teams/availability', headers=owner_headers, params={
        'start_time': start.isoformat(),
        'end_time': (start + timedelta(hours=2)).isoformat(),
        'required_officers': 1,
    }).json()
    assert inactive['id'] not in {
        officer['id']
        for officer in availability['available_officers'] + availability['unavailable_officers']
    }
    assert team['id'] not in {
        row['id']
        for row in availability['available_teams'] + availability['unavailable_teams']
    }


@pytest.mark.skipif(
    engine.dialect.name != 'postgresql',
    reason='Row-lock concurrency validation requires PostgreSQL',
)
def test_concurrent_double_booking_is_serialized():
    _, owner_headers = register_owner()
    officer, _ = invite_and_accept(owner_headers, 'Concurrent Officer')
    start = datetime.now(timezone.utc) + timedelta(days=2)

    def create(name):
        with TestClient(app) as concurrent_client:
            return concurrent_client.post('/api/v1/patrols/', headers=owner_headers, json={
                'name': name,
                'start_time': start.isoformat(),
                'end_time': (start + timedelta(hours=2)).isoformat(),
                'required_officers': 1,
                'officer_ids': [officer['id']],
            }).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(create, ['Concurrent A', 'Concurrent B']))
    assert sorted(statuses) == [200, 409]
