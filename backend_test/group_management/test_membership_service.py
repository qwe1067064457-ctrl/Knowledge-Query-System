from __future__ import annotations

import unittest

try:
    from .helpers import make_service, seed_user, temp_backend_dir
except ImportError:  # pragma: no cover - supports direct unittest discovery from this folder.
    from helpers import make_service, seed_user, temp_backend_dir

from backend.group_management import NotFoundError, ValidationError


class MembershipServiceTests(unittest.TestCase):
    def _seed_group(self, service):
        seed_user(service, "owner")
        service.create_group(group_id="law", name="Law KB", created_by="owner")

    def test_add_member_adds_active_user(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            self._seed_group(service)
            seed_user(service, "u1")

            member = service.add_member("law", "u1", "member")
            members = service.list_members("law")

            self.assertEqual(member["user_id"], "u1")
            self.assertEqual(member["role"], "member")
            self.assertIn("u1", {item["user_id"] for item in members})

    def test_add_member_rejects_disabled_missing_user_and_missing_group(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            self._seed_group(service)
            seed_user(service, "disabled")
            service.delete_user("disabled")

            with self.assertRaises(ValidationError):
                service.add_member("law", "disabled", "member")

            with self.assertRaises(NotFoundError):
                service.add_member("law", "missing", "member")

            with self.assertRaises(NotFoundError):
                service.add_member("missing_group", "disabled", "member")

    def test_add_member_repeated_user_updates_role_without_duplicate(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            self._seed_group(service)
            seed_user(service, "u1")

            service.add_member("law", "u1", "member")
            updated = service.add_member("law", "u1", "admin")
            members = [item for item in service.list_members("law") if item["user_id"] == "u1"]

            self.assertEqual(updated["role"], "admin")
            self.assertEqual(len(members), 1)
            self.assertEqual(members[0]["role"], "admin")

    def test_remove_member_is_soft_remove_and_default_list_filters_removed(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            self._seed_group(service)
            seed_user(service, "u1")
            service.add_member("law", "u1", "member")

            removed = service.remove_member("law", "u1")
            visible = service.list_members("law")
            all_members = service.list_members("law", include_removed=True)

            self.assertEqual(removed["status"], "removed")
            self.assertNotIn("u1", {item["user_id"] for item in visible})
            self.assertIn("u1", {item["user_id"] for item in all_members})

    def test_remove_missing_member_raises_not_found(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            self._seed_group(service)

            with self.assertRaises(NotFoundError):
                service.remove_member("law", "missing")


if __name__ == "__main__":
    unittest.main()
