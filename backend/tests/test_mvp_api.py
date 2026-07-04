import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


def auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


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
    assert register_response.status_code == 200
    registered = register_response.json()
    assert registered['email'] == email
    assert registered['name'] == 'MVP Guard'
    assert registered['role'] in {'admin', 'officer'}

    login_response = client.post('/api/login', json={'email': email, 'password': password})
    assert login_response.status_code == 200
    token = login_response.json()['access_token']

    user_response = client.get('/api/user', headers=auth_headers(token))
    assert user_response.status_code == 200
    assert user_response.json()['email'] == email

    patrol_response = client.post(
        '/api/patrol',
        json={'location': 'North Gate', 'status': 'completed'},
        headers=auth_headers(token),
    )
    assert patrol_response.status_code == 200
    patrol_log = patrol_response.json()
    assert patrol_log['location'] == 'North Gate'
    assert patrol_log['status'] == 'completed'

    patrol_list_response = client.get('/api/patrol', headers=auth_headers(token))
    assert patrol_list_response.status_code == 200
    assert any(item['id'] == patrol_log['id'] for item in patrol_list_response.json())

    incident_response = client.post(
        '/api/incidents',
        json={'description': 'Broken lock found on loading bay door', 'severity': 'high'},
        headers=auth_headers(token),
    )
    assert incident_response.status_code == 200
    incident = incident_response.json()
    assert incident['description'] == 'Broken lock found on loading bay door'
    assert incident['severity'] == 'high'

    incident_list_response = client.get('/api/incidents', headers=auth_headers(token))
    assert incident_list_response.status_code == 200
    assert any(item['id'] == incident['id'] for item in incident_list_response.json())
