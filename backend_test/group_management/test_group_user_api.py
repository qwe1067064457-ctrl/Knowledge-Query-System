from __future__ import annotations

import unittest

try:
    from .helpers import make_api_client, make_service, temp_backend_dir
except ImportError:  # pragma: no cover - supports direct unittest discovery from this folder.
    from helpers import make_api_client, make_service, temp_backend_dir


class GroupUserApiTests(unittest.TestCase):
    def test_user_api_create_duplicate_list_and_delete(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            client = make_api_client(service)

            created = client.post("/api/users", json={"id": "u1", "display_name": "Alice"})
            duplicate = client.post("/api/users", json={"id": "u1"})
            deleted = client.delete("/api/users/u1")
            listed = client.get("/api/users")
            listed_all = client.get("/api/users", params={"include_disabled": True})

            self.assertEqual(created.status_code, 200)
            self.assertEqual(created.json()["id"], "u1")
            self.assertEqual(duplicate.status_code, 409)
            self.assertEqual(deleted.status_code, 200)
            self.assertEqual(deleted.json()["status"], "disabled")
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(listed.json(), [])
            self.assertEqual(len(listed_all.json()), 1)

    def test_group_api_create_initializes_layout_and_missing_creator_returns_404(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            client = make_api_client(service)
            client.post("/api/users", json={"id": "u1"})

            created = client.post(
                "/api/groups",
                json={
                    "id": "law",
                    "name": "Law KB",
                    "created_by": "u1",
                    "default_agent_id": "legal_qa",
                },
            )
            missing_creator = client.post(
                "/api/groups",
                json={"id": "medical", "name": "Medical KB", "created_by": "missing"},
            )

            self.assertEqual(created.status_code, 200)
            self.assertEqual(created.json()["id"], "law")
            self.assertTrue((backend_dir / "storage" / "groups" / "law" / "meta.json").exists())
            self.assertTrue((backend_dir / "knowledge" / "groups" / "law" / "documents").exists())
            self.assertEqual(missing_creator.status_code, 404)

    def test_group_api_archive_filters_default_list(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            client = make_api_client(service)
            client.post("/api/users", json={"id": "u1"})
            client.post("/api/groups", json={"id": "law", "name": "Law KB", "created_by": "u1"})

            archived = client.post("/api/groups/law/archive")
            listed = client.get("/api/groups")
            listed_all = client.get("/api/groups", params={"include_archived": True})

            self.assertEqual(archived.status_code, 200)
            self.assertEqual(archived.json()["status"], "archived")
            self.assertEqual(listed.json(), [])
            self.assertEqual(len(listed_all.json()), 1)

    def test_group_api_member_add_and_soft_remove(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            client = make_api_client(service)
            client.post("/api/users", json={"id": "owner"})
            client.post("/api/users", json={"id": "u1"})
            client.post("/api/groups", json={"id": "law", "name": "Law KB", "created_by": "owner"})

            added = client.post("/api/groups/law/members", json={"user_id": "u1", "role": "viewer"})
            removed = client.delete("/api/groups/law/members/u1")
            visible = client.get("/api/groups/law/members")
            all_members = client.get("/api/groups/law/members", params={"include_removed": True})

            self.assertEqual(added.status_code, 200)
            self.assertEqual(added.json()["role"], "viewer")
            self.assertEqual(removed.status_code, 200)
            self.assertEqual(removed.json()["status"], "removed")
            self.assertNotIn("u1", {item["user_id"] for item in visible.json()})
            self.assertIn("u1", {item["user_id"] for item in all_members.json()})

    def test_api_invalid_id_maps_to_400(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            client = make_api_client(service)

            response = client.post("/api/users", json={"id": "../bad"})

            self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
