import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def create_token(prefix: str):
    email = f"{prefix}+{uuid.uuid4().hex}@example.com"
    password = "TestPass123!"
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Tenant Test User",
            "password": password,
            "organisation_name": f"{prefix.title()} Security {uuid.uuid4().hex[:8]}",
        },
    )
    assert register_response.status_code == 200

    token_response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert token_response.status_code == 200
    return token_response.json()["access_token"]


def test_patrols_are_scoped_to_authenticated_organisation():
    tenant_a_token = create_token("tenant-a")
    tenant_b_token = create_token("tenant-b")

    tenant_a_headers = {"Authorization": f"Bearer {tenant_a_token}"}
    tenant_b_headers = {"Authorization": f"Bearer {tenant_b_token}"}

    create_response = client.post(
        "/api/v1/patrols/",
        json={
            "name": "Tenant A restricted patrol",
            "description": "Should not leak to tenant B",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "assigned_to": "Alpha Team",
        },
        headers=tenant_a_headers,
    )
    assert create_response.status_code == 200
    patrol_id = create_response.json()["id"]

    tenant_b_list = client.get("/api/v1/patrols/", headers=tenant_b_headers)
    assert tenant_b_list.status_code == 200
    assert patrol_id not in [item["id"] for item in tenant_b_list.json()]

    tenant_b_get = client.get(f"/api/v1/patrols/{patrol_id}", headers=tenant_b_headers)
    assert tenant_b_get.status_code == 404
