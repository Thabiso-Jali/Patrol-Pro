import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from backend.app import models
from backend.app.database import SessionLocal, engine
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

    immutable = client.put(
        f"/api/v1/alerts/{created.json()['id']}",
        headers={**headers, 'X-Correlation-ID': 'incident-test-correlation'},
        json={**resolved.json(), 'resolution_notes': 'Attempted silent rewrite.'},
    )
    assert immutable.status_code == 409
    assert immutable.headers['X-Correlation-ID'] == 'incident-test-correlation'
    assert immutable.json() == {
        'error': {
            'code': 'IMMUTABLE_RECORD',
            'message': 'Incident in resolved cannot be edited. Create a correction, amendment, or replacement version instead.',
            'field_errors': [],
            'correlation_id': 'incident-test-correlation',
            'retryable': False,
        },
    }

    listed = client.get('/api/v1/alerts/', headers=headers)
    assert listed.status_code == 200
    assert [row['id'] for row in listed.json()] == [created.json()['id']]


def create_open_incident(headers, title='Concurrent incident'):
    response = client.post('/api/v1/alerts/', headers=headers, json={
        'title': title, 'description': 'Race-test incident.', 'category': 'security',
        'location': 'Gate', 'severity': 'high', 'status': 'open',
        'reported_at': datetime.now(timezone.utc).isoformat(),
    })
    assert response.status_code == 200
    return response.json()


@pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='Requires PostgreSQL row locks')
def test_incident_resolution_vs_cancellation_has_one_winner():
    headers = owner_headers()
    incident = create_open_incident(headers)
    barrier = Barrier(2)

    def transition(target):
        barrier.wait()
        with TestClient(app) as concurrent_client:
            return concurrent_client.put(
                f"/api/v1/alerts/{incident['id']}",
                headers={**headers, 'If-Match': str(incident['record_version'])},
                json={
                    **incident, 'status': target,
                    'resolution_notes': f'Incident {target} by authorised controller.',
                },
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(transition, ['resolved', 'cancelled']))
    assert sorted(statuses) == [200, 409]
    current = client.get(f"/api/v1/alerts/{incident['id']}", headers=headers).json()
    assert current['status'] in {'resolved', 'cancelled'}
    assert current['record_version'] == incident['record_version'] + 1


@pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='Requires PostgreSQL row locks')
def test_repeated_incident_resolution_replays_without_duplicate_event():
    headers = owner_headers()
    incident = create_open_incident(headers, 'Idempotent resolution')
    barrier = Barrier(2)
    key = f'incident-resolution-{uuid.uuid4().hex}'

    def resolve(_):
        barrier.wait()
        with TestClient(app) as concurrent_client:
            response = concurrent_client.put(
                f"/api/v1/alerts/{incident['id']}",
                headers={
                    **headers, 'If-Match': str(incident['record_version']),
                    'Idempotency-Key': key,
                },
                json={
                    **incident, 'status': 'resolved',
                    'resolution_notes': 'Resolved once with an authoritative command.',
                },
            )
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(resolve, range(2)))
    assert [status for status, _ in results] == [200, 200]
    assert results[0][1]['id'] == results[1][1]['id'] == incident['id']
    with SessionLocal() as db:
        organisation_id = db.get(models.Alert, incident['id']).organisation_id
        assert db.query(models.AuditLog).filter_by(
            organisation_id=organisation_id, action='alert.update',
            entity_id=str(incident['id']),
        ).count() == 1
