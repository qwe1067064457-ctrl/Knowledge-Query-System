from __future__ import annotations

import unittest

try:
    from .helpers import read_json, temp_backend_dir, make_service
except ImportError:  # pragma: no cover - supports direct unittest discovery from this folder.
    from helpers import read_json, temp_backend_dir, make_service

from backend.group_management import ConflictError, ValidationError


class UserServiceTests(unittest.TestCase):
    def test_create_user_persists_profile_and_registry(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)

            user = service.create_user(
                user_id="u1",
                display_name="Alice",
                metadata={"team": "qa"},
            )

            profile_path = backend_dir / "storage" / "users" / "u1" / "profile.json"
            registry_path = backend_dir / "storage" / "users" / "registry.json"
            profile = read_json(profile_path)
            registry = read_json(registry_path)

            self.assertEqual(user["id"], "u1")
            self.assertEqual(profile["display_name"], "Alice")
            self.assertEqual(profile["metadata"], {"team": "qa"})
            self.assertEqual(registry["items"][0]["id"], "u1")

    def test_create_user_rejects_duplicate_and_invalid_id(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            service.create_user(user_id="u1")

            with self.assertRaises(ConflictError):
                service.create_user(user_id="u1")

            with self.assertRaises(ValidationError):
                service.create_user(user_id="../bad")

    def test_delete_user_is_soft_delete_and_default_list_filters_disabled(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            service.create_user(user_id="u1")

            deleted = service.delete_user("u1")
            active_users = service.list_users()
            all_users = service.list_users(include_disabled=True)
            profile_path = backend_dir / "storage" / "users" / "u1" / "profile.json"

            self.assertEqual(deleted["status"], "disabled")
            self.assertTrue(profile_path.exists())
            self.assertEqual(active_users, [])
            self.assertEqual(len(all_users), 1)
            self.assertEqual(all_users[0]["status"], "disabled")

    def test_update_user_preserves_metadata_round_trip(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            service.create_user(user_id="u1", metadata={"theme": "light"})

            updated = service.update_user(
                "u1",
                display_name="Updated",
                metadata={"theme": "dark", "locale": "zh-CN"},
            )

            self.assertEqual(updated["display_name"], "Updated")
            self.assertEqual(updated["metadata"], {"theme": "dark", "locale": "zh-CN"})
            self.assertEqual(service.get_user("u1")["metadata"]["locale"], "zh-CN")

    def test_broken_registry_is_treated_as_empty_registry(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            registry_path = backend_dir / "storage" / "users" / "registry.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text("{broken", encoding="utf-8")

            self.assertEqual(service.list_users(), [])


if __name__ == "__main__":
    unittest.main()
