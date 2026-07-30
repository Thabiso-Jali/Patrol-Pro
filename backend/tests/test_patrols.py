import uuid
from datetime import datetime, timedelta, timezone
import unittest

from fastapi.testclient import TestClient
from backend.app.main import app


class PatrolFlowTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.email = f"patroluser+{uuid.uuid4().hex}@example.com"
        self.password = "TestPass123!"
        register_payload = {
            "email": self.email,
            "full_name": "Patrol User",
            "password": self.password,
        }
        response = self.client.post("/api/v1/auth/register", json=register_payload)
        self.assertEqual(response.status_code, 200)

        token_payload = {
            "username": self.email,
            "password": self.password,
        }
        token_response = self.client.post("/api/v1/auth/token", data=token_payload)
        self.assertEqual(token_response.status_code, 200)
        self.token = token_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {self.token}"}
        invitation = self.client.post("/api/v1/invitations", headers=headers, json={
            "email": f"patrol-officer+{uuid.uuid4().hex}@example.com",
            "full_name": "Assigned Patrol Officer",
            "role": "employee",
        })
        accepted = self.client.post("/api/v1/invitations/accept", json={
            "token": invitation.json()["invitation_token"],
            "password": "AssignedPass123!",
        })
        self.officer_id = accepted.json()["id"]

    def test_create_and_list_patrol(self):
        patrol_payload = {
            "name": "Night patrol",
            "description": "Check perimeter and gates",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
            "officer_ids": [self.officer_id],
        }
        headers = {"Authorization": f"Bearer {self.token}"}

        create_response = self.client.post("/api/v1/patrols/", json=patrol_payload, headers=headers)
        self.assertEqual(create_response.status_code, 200)
        patrol = create_response.json()
        self.assertEqual(patrol["name"], patrol_payload["name"])
        self.assertEqual(patrol["officer_ids"], [self.officer_id])
        self.assertIn("id", patrol)

        list_response = self.client.get("/api/v1/patrols/", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        patrols = list_response.json()
        self.assertTrue(any(item["id"] == patrol["id"] for item in patrols))


if __name__ == "__main__":
    unittest.main()
