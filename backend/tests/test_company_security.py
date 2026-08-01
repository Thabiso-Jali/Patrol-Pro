import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from backend.app.api.api_v1.endpoints import invitations as invitation_endpoint
from backend.app.config import Settings
from backend.app.main import app
from backend.tests.invitation_test_utils import post_development_invitation

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
    invitation = post_development_invitation(client, headers=headers, json={
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


def test_invitation_tokens_are_hidden_by_default_and_in_production():
    _, headers = register_company('HiddenInvitation')
    invitation_endpoint.settings.EXPOSE_DEVELOPMENT_INVITATION_TOKENS = False
    response = client.post('/api/v1/invitations', headers=headers, json={
        'full_name': 'Hidden Token Employee',
        'email': f"hidden-token+{uuid.uuid4().hex}@example.com",
        'role': 'employee',
    })
    assert response.status_code == 201
    assert 'invitation_token' not in response.json()

    previous_environment = invitation_endpoint.settings.APP_ENV
    previous_exposure = invitation_endpoint.settings.EXPOSE_DEVELOPMENT_INVITATION_TOKENS
    invitation_endpoint.settings.APP_ENV = 'production'
    invitation_endpoint.settings.EXPOSE_DEVELOPMENT_INVITATION_TOKENS = False
    try:
        production_response = client.post('/api/v1/invitations', headers=headers, json={
            'full_name': 'Production Hidden Token',
            'email': f"production-hidden+{uuid.uuid4().hex}@example.com",
            'role': 'employee',
        })
    finally:
        invitation_endpoint.settings.APP_ENV = previous_environment
        invitation_endpoint.settings.EXPOSE_DEVELOPMENT_INVITATION_TOKENS = previous_exposure
    assert production_response.status_code == 201
    assert 'invitation_token' not in production_response.json()


def test_development_token_exposure_is_disabled_by_default_and_rejected_in_production():
    development = Settings(_env_file=None)
    assert development.EXPOSE_DEVELOPMENT_INVITATION_TOKENS is False
    assert development.expose_invitation_tokens is False

    with pytest.raises(ValidationError, match='can only be enabled in development'):
        Settings(
            _env_file=None,
            APP_ENV='production',
            DATABASE_URL='postgresql+psycopg://example.invalid/patrol_pro',
            JWT_SECRET_KEY='temporary-test-secret-that-is-longer-than-32-characters',
            DEBUG=False,
            EXPOSE_DEVELOPMENT_INVITATION_TOKENS=True,
        )

    with pytest.raises(ValidationError, match='can only be enabled in development'):
        Settings(
            _env_file=None,
            APP_ENV='demo',
            DATABASE_URL='postgresql+psycopg://example.invalid/patrol_pro',
            JWT_SECRET_KEY='temporary-test-secret-that-is-longer-than-32-characters',
            DEBUG=False,
            EXPOSE_DEVELOPMENT_INVITATION_TOKENS='1',
        )

    with pytest.raises(ValidationError, match='valid boolean'):
        Settings(
            _env_file=None,
            EXPOSE_DEVELOPMENT_INVITATION_TOKENS='not-a-boolean',
        )


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
    replacement_tokens = client.post('/api/v1/auth/token', data={
        'username': email,
        'password': password,
    })
    assert replacement_tokens.status_code == 200
    assert client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f"Bearer {replacement_tokens.json()['access_token']}"},
    ).status_code == 200
