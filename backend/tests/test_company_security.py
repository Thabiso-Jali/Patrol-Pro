import uuid

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
