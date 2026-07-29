import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


def test_mvp_auth_patrol_and_incident_flow():
    client = TestClient(app)
    email = f'mvp+{uuid.uuid4().hex}@example.com'
    password = 'StrongPass123!'

    register_response = client.post(
        '/api/register',
        json={
            'name': 'MVP Guard',
            'email': email,
            'password': password,
            'role': 'guard',
        },
    )
    assert register_response.status_code == 410
    assert 'self-registration is disabled' in register_response.json()['detail']
