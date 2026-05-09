from __future__ import annotations

import unittest
from datetime import date

from helpers import TEST_TMP_ROOT, make_memory_system, temp_workspace


class MemorySearchSwitchTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        try:
            TEST_TMP_ROOT.rmdir()
        except OSError:
            pass

    def _seed_all_memory_types(self, workspace):
        memory = make_memory_system(workspace)
        memory.write_core_memory(
            user_id="u1",
            group_id="law",
            scope="user_group",
            content="违约责任回答优先引用法条。",
            title="核心记忆",
        )
        memory.write_daily_log(
            "law",
            "default",
            "今天继续讨论违约责任和赔偿范围。",
            target_date=date(2026, 5, 8),
            user_id="u1",
            title="日志",
        )
        memory.write_domain_case(
            group_id="law",
            title="违约责任案例",
            content="案例强调违约责任和可预见规则。",
        )
        return memory

    def test_search_can_disable_core_results(self) -> None:
        with temp_workspace() as workspace:
            memory = self._seed_all_memory_types(workspace)
            results = memory.search(
                "law",
                "default",
                "违约责任",
                user_id="u1",
                include_core=False,
                min_score=0.01,
            )
            self.assertTrue(results)
            self.assertNotIn("core", {item.memory_type for item in results})

    def test_search_can_disable_daily_log_results(self) -> None:
        with temp_workspace() as workspace:
            memory = self._seed_all_memory_types(workspace)
            results = memory.search(
                "law",
                "default",
                "违约责任",
                user_id="u1",
                include_daily_logs=False,
                min_score=0.01,
            )
            self.assertTrue(results)
            self.assertNotIn("daily_log", {item.memory_type for item in results})

    def test_search_can_disable_domain_case_results(self) -> None:
        with temp_workspace() as workspace:
            memory = self._seed_all_memory_types(workspace)
            results = memory.search(
                "law",
                "default",
                "违约责任",
                user_id="u1",
                include_domain_cases=False,
                min_score=0.01,
            )
            self.assertTrue(results)
            self.assertNotIn("domain_case", {item.memory_type for item in results})

    def test_search_returns_mixed_results_when_all_enabled(self) -> None:
        with temp_workspace() as workspace:
            memory = self._seed_all_memory_types(workspace)
            results = memory.search(
                "law",
                "default",
                "违约责任",
                user_id="u1",
                top_k=10,
                min_score=0.01,
            )
            memory_types = {item.memory_type for item in results}
            self.assertEqual(memory_types, {"core", "daily_log", "domain_case"})


if __name__ == "__main__":
    unittest.main()
