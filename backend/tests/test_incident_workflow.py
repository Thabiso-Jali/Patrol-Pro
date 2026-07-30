import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def owner_headers():
    unique = uuid.uuid4().hex
    email = f'incident-owner+{unique}@example.com'
    password = 'StrongPass123!'
    registered = client.post('/api/v1/auth/register', json={
        'company_name': f'Incident Security {unique}',
        'business_email': email,
        'owner_name': 'Incident Owner',
        'owner_email': email,
        'password': password,
    })
    assert registered.status_code == 200
    token = client.post('/api/v1/auth/token', data={'username': email, 'password': password})
    return {'Authorization': f"Bearer {token.json()['access_token']}"}


def test_incidents_are_persisted_and_terminal_status_requires_resolution():
    headers = owner_headers()
    created = client.post('/api/v1/alerts/', headers=headers, json={
        'title': 'Forced gate',
        'description': 'Gate lock showed visible damage.',
        'category': 'access_control',
        'location': 'North gate',
        'severity': 'high',
        'status': 'open',
        'reported_at': datetime.now(timezone.utc).isoformat(),
    })
    assert created.status_code == 200
    assert created.json()['reported_by'] is not None

    missing_resolution = client.put(
        f"/api/v1/alerts/{created.json()['id']}",
        headers=headers,
        json={**created.json(), 'status': 'resolved', 'resolution_notes': ''},
    )
    assert missing_resolution.status_code == 422

    resolved = client.put(
        f"/api/v1/alerts/{created.json()['id']}",
        headers=headers,
        json={
            **created.json(),
            'status': 'resolved',
            'resolution_notes': 'Lock replaced and site manager notified.',
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()['status'] == 'resolved'

    listed = client.get('/api/v1/alerts/', headers=headers)
    assert listed.status_code == 200
    assert [row['id'] for row in listed.json()] == [created.json()['id']]
