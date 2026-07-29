import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def register_company(prefix: str):
    email = f'{prefix}+{uuid.uuid4().hex}@example.com'
    password = 'StrongPass123!'
    response = client.post('/api/v1/auth/register', json={
        'company_name': f'{prefix} Security',
        'business_email': email,
        'owner_name': f'{prefix} Owner',
        'owner_email': email,
        'password': password,
        'timezone': 'Europe/London',
    })
    assert response.status_code == 200
    token = client.post('/api/v1/auth/token', data={'username': email, 'password': password})
    assert token.status_code == 200
    return response.json(), {'Authorization': f"Bearer {token.json()['access_token']}"}


def test_company_owner_invites_employee_and_token_is_single_use():
    registration, headers = register_company('Invitation')
    owner_context = client.get('/api/v1/auth/me', headers=headers)
    assert owner_context.status_code == 200
    assert owner_context.json()['role'] == 'company_owner'
    assert 'company.manage' in owner_context.json()['permissions']
    invitation = client.post('/api/v1/invitations', headers=headers, json={
        'full_name': 'Invited Employee',
        'email': f"employee+{uuid.uuid4().hex}@example.com",
        'role': 'employee',
    })
    assert invitation.status_code == 201
    accepted = client.post('/api/v1/invitations/accept', json={
        'token': invitation.json()['invitation_token'],
        'password': 'EmployeePass123!',
    })
    assert accepted.status_code == 201
    assert accepted.json()['organisation_id'] == registration['company']['id']
    assert accepted.json()['role'] == 'employee'
    reused = client.post('/api/v1/invitations/accept', json={
        'token': invitation.json()['invitation_token'],
        'password': 'EmployeePass123!',
    })
    assert reused.status_code == 400

    employee_tokens = client.post('/api/v1/auth/token', data={
        'username': invitation.json()['email'],
        'password': 'EmployeePass123!',
    })
    employee_headers = {'Authorization': f"Bearer {employee_tokens.json()['access_token']}"}
    employee_context = client.get('/api/v1/auth/me', headers=employee_headers)
    assert employee_context.status_code == 200
    assert employee_context.json()['role'] == 'employee'
    assert 'patrols.view' in employee_context.json()['permissions']
    assert 'users.view' not in employee_context.json()['permissions']
    assert client.get('/api/v1/audit-logs/', headers=employee_headers).status_code == 403
    assert client.post('/api/v1/patrols/', headers=employee_headers, json={
        'name': 'Unauthorized patrol administration',
        'assigned_to': 'Invited Employee',
    }).status_code == 403
    incident = client.post('/api/v1/alerts/', headers=employee_headers, json={
        'title': 'Employee reported incident',
        'severity': 'medium',
        'status': 'open',
        'reported_at': datetime.now(timezone.utc).isoformat(),
    })
    assert incident.status_code == 200
    assert client.delete(
        f"/api/v1/alerts/{incident.json()['id']}",
        headers=employee_headers,
    ).status_code == 403


def test_logout_revokes_access_and_refresh_tokens():
    email = f'revoke+{uuid.uuid4().hex}@example.com'
    password = 'StrongPass123!'
    client.post('/api/v1/auth/register', json={
        'company_name': 'Revocation Two',
        'business_email': email,
        'owner_name': 'Revocation Owner',
        'owner_email': email,
        'password': password,
    })
    tokens = client.post('/api/v1/auth/token', data={'username': email, 'password': password}).json()
    auth = {'Authorization': f"Bearer {tokens['access_token']}"}
    assert client.post('/api/v1/auth/logout', headers=auth).status_code == 204
    assert client.get('/api/v1/dashboard/stats', headers=auth).status_code == 401
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401
