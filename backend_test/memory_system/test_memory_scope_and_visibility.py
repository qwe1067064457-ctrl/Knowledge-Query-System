from __future__ import annotations

import unittest
from datetime import date

from helpers import TEST_TMP_ROOT, make_memory_system, temp_workspace


class MemoryScopeVisibilityTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        try:
            TEST_TMP_ROOT.rmdir()
        except OSError:
            pass

    def test_get_core_memories_returns_user_global_and_user_group_together(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)
            memory.write_core_memory(
                user_id="u1",
                group_id=None,
                scope="user_global",
                content="默认中文输出。",
            )
            memory.write_core_memory(
                user_id="u1",
                group_id="law",
                scope="user_group",
                content="法律组优先引用法条。",
            )

            results = memory.get_core_memories(user_id="u1", group_id="law")
            joined = "\n".join(item.content for item in results)
            self.assertIn("默认中文输出。", joined)
            self.assertIn("法律组优先引用法条。", joined)

    def test_get_core_memories_excludes_other_group_user_group_memory(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)
            memory.write_core_memory(
                user_id="u1",
                group_id=None,
                scope="user_global",
                content="默认中文输出。",
            )
            memory.write_core_memory(
                user_id="u1",
                group_id="law",
                scope="user_group",
                content="法律组优先引用法条。",
            )

            results = memory.get_core_memories(user_id="u1", group_id="medical")
            joined = "\n".join(item.content for item in results)
            self.assertIn("默认中文输出。", joined)
            self.assertNotIn("法律组优先引用法条。", joined)

    def test_daily_log_isolated_by_user_and_group(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)
            memory.write_daily_log(
                "law",
                "default",
                "law/u1 日志",
                target_date=date(2026, 5, 8),
                user_id="u1",
            )
            memory.write_daily_log(
                "law",
                "default",
                "law/u2 日志",
                target_date=date(2026, 5, 8),
                user_id="u2",
            )
            memory.write_daily_log(
                "medical",
                "default",
                "medical/u1 日志",
                target_date=date(2026, 5, 8),
                user_id="u1",
            )

            results = memory.search(
                "law",
                "default",
                "日志",
                user_id="u1",
                include_core=False,
                include_domain_cases=False,
                min_score=0.01,
            )
            joined = "\n".join(item.content for item in results)
            self.assertIn("law/u1 日志", joined)
            self.assertNotIn("law/u2 日志", joined)
            self.assertNotIn("medical/u1 日志", joined)

    def test_domain_case_is_shared_within_group_only(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)
            memory.write_domain_case(
                group_id="law",
                title="违约责任案例",
                content="合同违约责任案例。",
            )
            memory.write_domain_case(
                group_id="medical",
                title="胸痛病例",
                content="胸痛风险分层案例。",
            )

            same_group = memory.search(
                "law",
                "default",
                "违约责任",
                user_id="u2",
                include_core=False,
                include_daily_logs=False,
                min_score=0.01,
            )
            other_group = memory.search(
                "medical",
                "default",
                "违约责任",
                user_id="u2",
                include_core=False,
                include_daily_logs=False,
                min_score=0.01,
            )
            self.assertTrue(same_group)
            self.assertEqual(same_group[0].scope, "group_shared")
            self.assertFalse(other_group)


if __name__ == "__main__":
    unittest.main()
