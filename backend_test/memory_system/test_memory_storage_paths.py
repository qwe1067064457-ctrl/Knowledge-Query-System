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
                content="默认使用中文输出。",
                title="输出偏好",
                tags=["style"],
            )

            path = workspace / "storage" / "users" / "u1" / "global" / "core.json"
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["items"][0]["scope"], "user_global")
            self.assertEqual(payload["items"][0]["memory_type"], "core")
            self.assertEqual(payload["items"][0]["content"], "默认使用中文输出。")

    def test_write_core_memory_persists_to_user_group_path(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)

            memory.write_core_memory(
                user_id="u1",
                group_id="law",
                scope="user_group",
                content="法律组优先引用法条。",
                title="法律组偏好",
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
                "今天确认 archive 仍可继续写入。",
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

    def test_write_domain_case_persists_to_group_shared_path(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)

            memory.write_domain_case(
                group_id="law",
                title="违约责任案例",
                content="合同违约责任需要结合损失赔偿和可预见规则分析。",
                tags=["contract"],
            )

            path = workspace / "storage" / "groups" / "law" / "shared" / "domain_cases.jsonl"
            self.assertTrue(path.exists())
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(rows[0]["scope"], "group_shared")
            self.assertEqual(rows[0]["memory_type"], "domain_case")
            self.assertEqual(rows[0]["title"], "违约责任案例")


if __name__ == "__main__":
    unittest.main()
