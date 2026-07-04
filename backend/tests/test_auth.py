import uuid

from fastapi.testclient import TestClient
from backend.app.main import app


def test_register_and_token_flow():
    client = TestClient(app)
    email = f"testuser+{uuid.uuid4().hex}@example.com"

    register_payload = {
        'email': email,
        'full_name': 'Test User',
        'password': 'testpass123',
    }

    response = client.post('/api/v1/auth/register', json=register_payload)
    assert response.status_code == 200
    data = response.json()
    assert data['email'] == register_payload['email']
    assert data['full_name'] == register_payload['full_name']
    assert 'id' in data

    token_payload = {
        'username': register_payload['email'],
        'password': register_payload['password'],
    }

    token_response = client.post('/api/v1/auth/token', data=token_payload)
    assert token_response.status_code == 200
    token_data = token_response.json()
    assert token_data['token_type'] == 'bearer'
    assert token_data['access_token']
