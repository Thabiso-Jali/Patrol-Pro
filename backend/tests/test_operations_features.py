import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def create_user_and_headers(prefix: str = "ops"):
    email = f"{prefix}+{uuid.uuid4().hex}@example.com"
    password = "TestPass123!"
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Operations User",
            "password": password,
            "organisation_name": f"Operations Security {uuid.uuid4().hex[:8]}",
        },
    )
    assert register_response.status_code == 200

    token_response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def create_patrol(headers):
    response = client.post(
        "/api/v1/patrols/",
        json={
            "name": "Live operations patrol",
            "description": "Perimeter verification",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "assigned_to": "Mobile Team",
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_checkpoint_tracking_notifications_and_reports_flow():
    headers = create_user_and_headers()
    patrol = create_patrol(headers)

    checkpoint_response = client.post(
        "/api/v1/checkpoints/",
        json={
            "name": "North Gate",
            "code": "QR-NORTH-001",
            "patrol_id": patrol["id"],
            "location_label": "North vehicle entrance",
            "latitude": 51.501,
            "longitude": -0.141,
            "nfc_tag": "NFC-NORTH-001",
            "status": "pending",
        },
        headers=headers,
    )
    assert checkpoint_response.status_code == 200
    checkpoint = checkpoint_response.json()
    assert checkpoint["status"] == "pending"

    verify_response = client.post(
        f"/api/v1/checkpoints/{checkpoint['id']}/verify",
        json={"code": "QR-NORTH-001", "latitude": 51.502, "longitude": -0.142},
        headers=headers,
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "verified"
    assert verify_response.json()["verified_at"]

    location_response = client.post(
        "/api/v1/tracking/locations",
        json={
            "patrol_id": patrol["id"],
            "latitude": 51.503,
            "longitude": -0.143,
            "accuracy_meters": 8.5,
            "battery_level": 86,
        },
        headers=headers,
    )
    assert location_response.status_code == 200
    assert location_response.json()["patrol_id"] == patrol["id"]

    latest_response = client.get("/api/v1/tracking/locations/latest", headers=headers)
    assert latest_response.status_code == 200
    assert any(item["patrol_id"] == patrol["id"] for item in latest_response.json())

    notification_response = client.post(
        "/api/v1/notifications/",
        json={
            "title": "Route priority updated",
            "body": "North Gate must be checked first.",
            "category": "dispatch",
            "priority": "high",
        },
        headers=headers,
    )
    assert notification_response.status_code == 200
    notification = notification_response.json()
    assert notification["read_at"] is None

    read_response = client.post(f"/api/v1/notifications/{notification['id']}/read", headers=headers)
    assert read_response.status_code == 200
    assert read_response.json()["read_at"]

    analytics_response = client.get("/api/v1/reports/analytics", headers=headers)
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["verified_checkpoints"] >= 1
    assert any(item["patrol_id"] == patrol["id"] for item in analytics["latest_locations"])
