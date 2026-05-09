from __future__ import annotations

import asyncio
import unittest
from datetime import date

from helpers import TEST_TMP_ROOT, make_memory_system, temp_workspace, write_group_meta


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
            content="Answer breach-liability questions with statute citations first.",
            title="Core memory",
        )
        memory.write_daily_log(
            "law",
            "default",
            "We continued the breach-liability discussion today.",
            target_date=date.today(),
            user_id="u1",
            title="Daily log",
        )
        memory.write_domain_case(
            group_id="law",
            title="Breach liability case",
            content="The case emphasizes foreseeability in breach liability.",
        )
        return memory

    def test_search_can_disable_core_results(self) -> None:
        with temp_workspace() as workspace:
            memory = self._seed_all_memory_types(workspace)
            results = memory.search(
                "law",
                "default",
                "breach liability",
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
                "breach liability",
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
                "breach liability",
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
                "breach liability",
                user_id="u1",
                top_k=10,
                min_score=0.01,
            )
            memory_types = {item.memory_type for item in results}
            self.assertEqual(memory_types, {"core", "daily_log", "domain_case"})

    def test_disabled_core_policy_prevents_core_promotion_during_flush(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                write_group_meta(
                    workspace,
                    "law",
                    {
                        "enabled_memory_types": ["daily_log", "domain_case"],
                        "core": {
                            "explicit_markers": ["ALWAYS"],
                            "group_scope_keywords": ["LAW"],
                            "min_candidate_length": 1,
                            "max_candidate_length": 120,
                        },
                        "daily_log": {"checkpoint_enabled": True},
                        "domain_case": {
                            "completion_markers": ["DONE"],
                            "structural_markers": ["ISSUE", "ANALYSIS", "CONCLUSION"],
                            "case_markers": ["CASE"],
                        },
                    },
                )
                memory = make_memory_system(workspace)

                result = await memory.flush_from_context(
                    "law",
                    "default",
                    "Checkpoint summary",
                    user_id="u1",
                    messages=[{"role": "user", "content": "ALWAYS answer in Chinese."}],
                )

                self.assertEqual(result["core_written"], 0)
                self.assertEqual(memory.get_core_memories(user_id="u1", group_id="law"), [])

        asyncio.run(run())

    def test_disabled_domain_case_policy_prevents_case_promotion_during_flush(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                write_group_meta(
                    workspace,
                    "law",
                    {
                        "enabled_memory_types": ["core", "daily_log"],
                        "core": {
                            "explicit_markers": ["ALWAYS"],
                            "group_scope_keywords": ["LAW"],
                            "min_candidate_length": 1,
                            "max_candidate_length": 120,
                        },
                        "daily_log": {"checkpoint_enabled": True},
                        "domain_case": {
                            "completion_markers": ["DONE"],
                            "structural_markers": ["ISSUE", "ANALYSIS", "CONCLUSION"],
                            "case_markers": ["CASE"],
                        },
                    },
                )
                memory = make_memory_system(workspace)

                result = await memory.flush_from_context(
                    "law",
                    "default",
                    "ISSUE: breach liability. ANALYSIS: compare facts. CONCLUSION: DONE.",
                    user_id="u1",
                    messages=[{"role": "assistant", "content": "ISSUE: breach liability. ANALYSIS: compare facts. CONCLUSION: DONE."}],
                )

                self.assertEqual(result["domain_case_written"], 0)
                results = memory.search(
                    "law",
                    "default",
                    "breach liability",
                    user_id="u1",
                    include_core=False,
                    include_daily_logs=False,
                    min_score=0.01,
                )
                self.assertFalse(results)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
