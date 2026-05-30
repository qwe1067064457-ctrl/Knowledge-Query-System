from __future__ import annotations

import unittest

try:
    from .helpers import make_service, read_json, seed_user, temp_backend_dir
except ImportError:  # pragma: no cover - supports direct unittest discovery from this folder.
    from helpers import make_service, read_json, seed_user, temp_backend_dir

from backend.group_management import ConflictError, NotFoundError, ValidationError


class GroupServiceTests(unittest.TestCase):
    def test_create_group_requires_existing_active_creator(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)

            with self.assertRaises(NotFoundError):
                service.create_group(group_id="law", name="Law KB", created_by="missing")

            seed_user(service, "u1")
            service.delete_user("u1")
            with self.assertRaises(ValidationError):
                service.create_group(group_id="law", name="Law KB", created_by="u1")

    def test_create_group_initializes_storage_members_and_knowledge_layout(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            seed_user(service, "u1")

            group = service.create_group(
                group_id="law",
                name="Law KB",
                created_by="u1",
                description="Legal knowledge",
                default_agent_id="legal_qa",
                metadata={"domain": "legal"},
            )

            meta_path = backend_dir / "storage" / "groups" / "law" / "meta.json"
            members_path = backend_dir / "storage" / "groups" / "law" / "members.json"
            knowledge_storage_dir = backend_dir / "storage" / "groups" / "law" / "knowledge"
            meta = read_json(meta_path)
            members = read_json(members_path)["items"]

            self.assertEqual(group["id"], "law")
            self.assertEqual(meta["default_agent_id"], "legal_qa")
            self.assertEqual(meta["metadata"], {"domain": "legal"})
            self.assertEqual(members[0]["user_id"], "u1")
            self.assertEqual(members[0]["role"], "owner")
            self.assertTrue((backend_dir / "storage" / "groups" / "law" / "users").exists())
            self.assertTrue((backend_dir / "storage" / "groups" / "law" / "registries" / "source_registry.jsonl").exists())
            self.assertEqual(read_json(knowledge_storage_dir / "meta" / "source_layout.json"), {})
            self.assertTrue((knowledge_storage_dir / "raw" / "cn").exists())
            self.assertTrue((knowledge_storage_dir / "raw" / "us").exists())
            self.assertTrue((knowledge_storage_dir / "raw" / "cases").exists())

    def test_create_group_writes_default_memory_policy_and_deep_merges_override(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            seed_user(service, "u1")

            group = service.create_group(
                group_id="law",
                name="Law KB",
                created_by="u1",
                memory_policy={"daily_log": {"checkpoint_enabled": False}},
            )

            policy = group["memory_policy"]
            self.assertFalse(policy["daily_log"]["checkpoint_enabled"])
            self.assertEqual(policy["enabled_memory_types"], ["core", "daily_log", "domain_case"])
            self.assertEqual(policy["core"]["explicit_markers"], ["always", "default"])

    def test_create_group_rejects_duplicate_and_invalid_id(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            seed_user(service, "u1")
            service.create_group(group_id="law", name="Law KB", created_by="u1")

            with self.assertRaises(ConflictError):
                service.create_group(group_id="law", name="Law KB", created_by="u1")

            with self.assertRaises(ValidationError):
                service.create_group(group_id="../bad", name="Bad", created_by="u1")

    def test_delete_group_archives_without_removing_layout_and_list_filters_archived(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            seed_user(service, "u1")
            service.create_group(group_id="law", name="Law KB", created_by="u1")

            archived = service.delete_group("law")
            active_groups = service.list_groups()
            all_groups = service.list_groups(include_archived=True)
            group_dir = backend_dir / "storage" / "groups" / "law"

            self.assertEqual(archived["status"], "archived")
            self.assertEqual(active_groups, [])
            self.assertEqual(len(all_groups), 1)
            self.assertTrue(group_dir.exists())
            self.assertFalse((backend_dir / "knowledge" / "groups" / "law").exists())

    def test_create_group_initializes_medicine_specific_raw_subdirs(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            seed_user(service, "u1")

            service.create_group(group_id="medicine", name="Medicine KB", created_by="u1")

            raw_root = backend_dir / "storage" / "groups" / "medicine" / "knowledge" / "raw"
            self.assertTrue((raw_root / "open_access_pdf").exists())
            self.assertTrue((raw_root / "pmc_ftp_pdf").exists())
            self.assertTrue((raw_root / "pmc_open_access").exists())
            self.assertTrue((raw_root / "yiigle_cn").exists())

    def test_missing_default_policy_still_allows_group_creation_with_empty_policy(self) -> None:
        with temp_backend_dir(with_policy=False) as backend_dir:
            service = make_service(backend_dir)
            seed_user(service, "u1")

            group = service.create_group(group_id="law", name="Law KB", created_by="u1")

            self.assertEqual(group["memory_policy"], {})

    def test_update_group_deep_merges_memory_policy_and_preserves_agent_as_metadata(self) -> None:
        with temp_backend_dir() as backend_dir:
            service = make_service(backend_dir)
            seed_user(service, "u1")
            service.create_group(
                group_id="law",
                name="Law KB",
                created_by="u1",
                default_agent_id="default",
            )

            updated = service.update_group(
                "law",
                default_agent_id="legal_qa",
                memory_policy={"core": {"min_candidate_length": 8}},
                metadata={"owner_note": "managed"},
            )

            self.assertEqual(updated["default_agent_id"], "legal_qa")
            self.assertEqual(updated["knowledge"]["storage_root"], "storage/groups/law/knowledge")
            self.assertEqual(updated["memory_policy"]["core"]["min_candidate_length"], 8)
            self.assertEqual(updated["memory_policy"]["core"]["explicit_markers"], ["always", "default"])
            self.assertEqual(updated["metadata"], {"owner_note": "managed"})


if __name__ == "__main__":
    unittest.main()
