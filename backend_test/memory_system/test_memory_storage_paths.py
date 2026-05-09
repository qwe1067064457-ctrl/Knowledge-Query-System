from __future__ import annotations

import json
import unittest
from datetime import date

from helpers import TEST_TMP_ROOT, make_memory_system, temp_workspace


class MemoryStoragePathTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        try:
            TEST_TMP_ROOT.rmdir()
        except OSError:
            pass

    def test_write_core_memory_persists_to_user_global_path(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)

            memory.write_core_memory(
                user_id="u1",
                group_id=None,
                scope="user_global",
                content="Default to Chinese output.",
                title="Output preference",
                tags=["style"],
            )

            path = workspace / "storage" / "users" / "u1" / "global" / "core.json"
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"][0]["scope"], "user_global")
            self.assertEqual(payload["items"][0]["memory_type"], "core")
            self.assertEqual(payload["items"][0]["content"], "Default to Chinese output.")

    def test_write_core_memory_persists_to_user_group_path(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)

            memory.write_core_memory(
                user_id="u1",
                group_id="law",
                scope="user_group",
                content="In the law group, cite statutes first.",
                title="Law-group preference",
            )

            path = workspace / "storage" / "users" / "u1" / "groups" / "law" / "core.json"
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"][0]["scope"], "user_group")
            self.assertEqual(payload["items"][0]["group_id"], "law")

    def test_write_daily_log_persists_to_user_group_daily_log_path(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)

            memory.write_daily_log(
                "law",
                "default",
                "Confirmed that archived sessions still allow new messages.",
                target_date=date(2026, 5, 8),
                user_id="u1",
                source_session_id="s1",
            )

            path = (
                workspace
                / "storage"
                / "users"
                / "u1"
                / "groups"
                / "law"
                / "daily_logs"
                / "2026-05-08.jsonl"
            )
            self.assertTrue(path.exists())
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(rows[0]["scope"], "user_group")
            self.assertEqual(rows[0]["memory_type"], "daily_log")
            self.assertEqual(rows[0]["source_session_id"], "s1")

    def test_write_to_daily_log_uses_same_storage_path_as_write_daily_log(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)

            memory.write_daily_log(
                "law",
                "default",
                "First log row",
                target_date=date(2026, 5, 8),
                user_id="u1",
            )
            memory.write_to_daily_log(
                "law",
                "default",
                "Second log row",
                target_date=date(2026, 5, 8),
                user_id="u1",
            )

            path = (
                workspace
                / "storage"
                / "users"
                / "u1"
                / "groups"
                / "law"
                / "daily_logs"
                / "2026-05-08.jsonl"
            )
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 2)
            self.assertEqual([row["content"] for row in rows], ["First log row", "Second log row"])

    def test_write_domain_case_persists_to_group_shared_path(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)

            memory.write_domain_case(
                group_id="law",
                title="Breach liability case",
                content="The case ties breach liability to loss allocation and foreseeability.",
                tags=["contract"],
            )

            path = workspace / "storage" / "groups" / "law" / "shared" / "domain_cases.jsonl"
            self.assertTrue(path.exists())
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(rows[0]["scope"], "group_shared")
            self.assertEqual(rows[0]["memory_type"], "domain_case")
            self.assertEqual(rows[0]["title"], "Breach liability case")


if __name__ == "__main__":
    unittest.main()
