import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def create_user_and_headers(prefix: str):
    unique = uuid.uuid4().hex
    email = f"{prefix}+{unique}@example.com"
    password = "TestPass123!"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Dashboard Supervisor",
            "password": password,
            "organisation_name": f"Dashboard Security {unique}",
            "role": "admin",
        },
    )
    assert response.status_code == 200
    token_response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def create_active_patrol(headers, name: str, officer_id: int):
    now = datetime.now(timezone.utc)
    response = client.post(
        "/api/v1/patrols/",
        json={
            "name": name,
            "description": "Dashboard aggregate test",
            "start_time": (now - timedelta(minutes=30)).isoformat(),
            "end_time": (now + timedelta(minutes=30)).isoformat(),
            "officer_ids": [officer_id],
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def create_officer(headers, name="Dashboard Officer"):
    officer_email = f"officer+{uuid.uuid4().hex}@example.com"
    invitation_response = client.post(
        "/api/v1/invitations",
        json={"email": officer_email, "full_name": name, "role": "employee"},
        headers=headers,
    )
    assert invitation_response.status_code == 201
    officer_response = client.post(
        "/api/v1/invitations/accept",
        json={
            "token": invitation_response.json()["invitation_token"],
            "password": "TestPass123!",
        },
    )
    assert officer_response.status_code == 201
    return officer_response.json(), officer_email


def test_dashboard_requires_authentication():
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 401


def test_empty_organisation_receives_zeros_and_empty_operational_data():
    headers = create_user_and_headers("dashboard-empty")

    response = client.get("/api/v1/dashboard/stats", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "active_patrols": 0,
        "officers": 0,
        "open_incidents": 0,
        "pending_checkpoints": 0,
        "completed_checkpoints": 0,
        "checkpoint_completion_rate": 0,
        "recent_activity": [
            {
                "action": "company.register",
                "entity_type": "organisation",
                "created_at": response.json()["recent_activity"][0]["created_at"],
            }
        ],
        "active_patrol_details": [],
        "todays_schedule": [],
    }


def test_dashboard_counts_are_live_and_organisation_scoped():
    first_headers = create_user_and_headers("dashboard-first")
    second_headers = create_user_and_headers("dashboard-second")
    first_officer, officer_email = create_officer(first_headers)
    second_officer, second_officer_email = create_officer(
        second_headers, "Second Dashboard Officer",
    )
    first_patrol = create_active_patrol(
        first_headers, "First organisation patrol", first_officer["id"],
    )
    create_active_patrol(
        second_headers, "Second organisation patrol", second_officer["id"],
    )

    first_officers = client.get("/api/v1/users/officers", headers=first_headers)
    second_officers = client.get("/api/v1/users/officers", headers=second_headers)
    assert first_officers.status_code == 200
    assert [user["email"] for user in first_officers.json()] == [officer_email]
    assert second_officers.status_code == 200
    assert [user["email"] for user in second_officers.json()] == [second_officer_email]

    alert_response = client.post(
        "/api/v1/alerts/",
        json={
            "title": "Open dashboard incident",
            "description": "Non-sensitive test event",
            "severity": "medium",
            "status": "open",
            "reported_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=first_headers,
    )
    assert alert_response.status_code == 200

    pending_response = client.post(
        "/api/v1/checkpoints/",
        json={
            "name": "Pending dashboard checkpoint",
            "code": f"PENDING-{uuid.uuid4().hex}",
            "patrol_id": first_patrol["id"],
            "status": "pending",
        },
        headers=first_headers,
    )
    assert pending_response.status_code == 200
    verified_response = client.post(
        "/api/v1/checkpoints/",
        json={
            "name": "Verified dashboard checkpoint",
            "code": f"VERIFIED-{uuid.uuid4().hex}",
            "patrol_id": first_patrol["id"],
            "status": "pending",
        },
        headers=first_headers,
    )
    assert verified_response.status_code == 200
    verify_response = client.post(
        f"/api/v1/checkpoints/{verified_response.json()['id']}/verify",
        json={"code": verified_response.json()["code"]},
        headers=first_headers,
    )
    assert verify_response.status_code == 200

    first_stats = client.get("/api/v1/dashboard/stats", headers=first_headers)
    second_stats = client.get("/api/v1/dashboard/stats", headers=second_headers)

    assert first_stats.status_code == 200
    assert first_stats.json()["active_patrols"] == 1
    assert first_stats.json()["officers"] == 1
    assert first_stats.json()["open_incidents"] == 1
    assert first_stats.json()["pending_checkpoints"] == 1
    assert first_stats.json()["completed_checkpoints"] == 1
    assert first_stats.json()["checkpoint_completion_rate"] == 50
    assert [item["name"] for item in first_stats.json()["active_patrol_details"]] == [
        "First organisation patrol"
    ]
    assert all("actor_email" not in item for item in first_stats.json()["recent_activity"])

    assert second_stats.status_code == 200
    assert second_stats.json()["active_patrols"] == 1
    assert second_stats.json()["officers"] == 1
    assert second_stats.json()["open_incidents"] == 0
    assert second_stats.json()["pending_checkpoints"] == 0
    assert second_stats.json()["completed_checkpoints"] == 0
    assert second_stats.json()["checkpoint_completion_rate"] == 0
    assert [item["name"] for item in second_stats.json()["active_patrol_details"]] == [
        "Second organisation patrol"
    ]
