import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from backend.app.main import app


client = TestClient(app)


def create_user_and_token():
    email = f"user+{uuid.uuid4().hex}@example.com"
    password = "TestPass123!"
    register_payload = {
        "email": email,
        "full_name": "Domain Test User",
        "password": password,
    }
    register_response = client.post("/api/v1/auth/register", json=register_payload)
    assert register_response.status_code == 200

    token_response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert token_response.status_code == 200
    access_token = token_response.json()["access_token"]
    return access_token


def test_device_flow():
    token = create_user_and_token()
    headers = {"Authorization": f"Bearer {token}"}

    device_payload = {
        "name": "Radio Unit",
        "serial_number": uuid.uuid4().hex,
        "status": "active",
    }
    create_response = client.post("/api/v1/devices/", json=device_payload, headers=headers)
    assert create_response.status_code == 200
    device = create_response.json()
    assert device["name"] == device_payload["name"]
    assert device["serial_number"] == device_payload["serial_number"]
    assert "id" in device

    list_response = client.get("/api/v1/devices/", headers=headers)
    assert list_response.status_code == 200
    devices = list_response.json()
    assert any(item["id"] == device["id"] for item in devices)


def test_customer_flow():
    token = create_user_and_token()
    headers = {"Authorization": f"Bearer {token}"}

    customer_payload = {
        "name": "Acme Security",
        "contact_email": "contact@acme.example.com",
        "phone": "555-1234",
        "address": "100 Main Street",
    }
    create_response = client.post("/api/v1/customers/", json=customer_payload, headers=headers)
    assert create_response.status_code == 200
    customer = create_response.json()
    assert customer["name"] == customer_payload["name"]
    assert customer["contact_email"] == customer_payload["contact_email"]
    assert "id" in customer

    list_response = client.get("/api/v1/customers/", headers=headers)
    assert list_response.status_code == 200
    customers = list_response.json()
    assert any(item["id"] == customer["id"] for item in customers)


def test_alert_flow():
    token = create_user_and_token()
    headers = {"Authorization": f"Bearer {token}"}

    alert_payload = {
        "title": "Unauthorized access",
        "description": "Gate left open after patrol",
        "severity": "high",
        "status": "open",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "patrol_id": None,
        "device_id": None,
        "customer_id": None,
    }
    create_response = client.post("/api/v1/alerts/", json=alert_payload, headers=headers)
    assert create_response.status_code == 200
    alert = create_response.json()
    assert alert["title"] == alert_payload["title"]
    assert alert["severity"] == alert_payload["severity"]
    assert "id" in alert

    list_response = client.get("/api/v1/alerts/", headers=headers)
    assert list_response.status_code == 200
    alerts = list_response.json()
    assert any(item["id"] == alert["id"] for item in alerts)
