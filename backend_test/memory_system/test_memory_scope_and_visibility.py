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
                content="Default to Chinese output.",
            )
            memory.write_core_memory(
                user_id="u1",
                group_id="law",
                scope="user_group",
                content="In the law group, cite statutes first.",
            )

            results = memory.get_core_memories(user_id="u1", group_id="law")
            payload = {(item.scope, item.content) for item in results}
            self.assertIn(("user_global", "Default to Chinese output."), payload)
            self.assertIn(("user_group", "In the law group, cite statutes first."), payload)

    def test_get_core_memories_excludes_other_group_user_group_memory(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)
            memory.write_core_memory(
                user_id="u1",
                group_id=None,
                scope="user_global",
                content="Default to Chinese output.",
            )
            memory.write_core_memory(
                user_id="u1",
                group_id="law",
                scope="user_group",
                content="In the law group, cite statutes first.",
            )

            results = memory.get_core_memories(user_id="u1", group_id="medical")
            payload = {(item.scope, item.content) for item in results}
            self.assertIn(("user_global", "Default to Chinese output."), payload)
            self.assertNotIn(("user_group", "In the law group, cite statutes first."), payload)

    def test_get_core_memories_does_not_fallback_to_default_user(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)
            memory.write_core_memory(
                user_id="default",
                group_id=None,
                scope="user_global",
                content="Legacy fallback memory.",
            )
            memory.write_core_memory(
                user_id="u1",
                group_id=None,
                scope="user_global",
                content="Real user memory.",
            )

            results = memory.get_core_memories(user_id="u1", group_id="law")
            payload = {(item.scope, item.content) for item in results}
            self.assertIn(("user_global", "Real user memory."), payload)
            self.assertNotIn(("user_global", "Legacy fallback memory."), payload)

    def test_daily_log_isolated_by_user_and_group(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)
            memory.write_daily_log(
                "law",
                "default",
                "law/u1 timeline",
                target_date=date.today(),
                user_id="u1",
            )
            memory.write_daily_log(
                "law",
                "default",
                "law/u2 timeline",
                target_date=date.today(),
                user_id="u2",
            )
            memory.write_daily_log(
                "medical",
                "default",
                "medical/u1 timeline",
                target_date=date.today(),
                user_id="u1",
            )

            results = memory.search(
                "law",
                "default",
                "timeline",
                user_id="u1",
                include_core=False,
                include_domain_cases=False,
                min_score=0.01,
            )
            contents = {item.content for item in results}
            self.assertIn("law/u1 timeline", contents)
            self.assertNotIn("law/u2 timeline", contents)
            self.assertNotIn("medical/u1 timeline", contents)

    def test_domain_case_is_shared_within_group_only(self) -> None:
        with temp_workspace() as workspace:
            memory = make_memory_system(workspace)
            memory.write_domain_case(
                group_id="law",
                title="Breach liability case",
                content="A law-group shared case.",
            )
            memory.write_domain_case(
                group_id="medical",
                title="Chest pain case",
                content="A medical-group shared case.",
            )

            same_group = memory.search(
                "law",
                "default",
                "breach liability",
                user_id="u2",
                include_core=False,
                include_daily_logs=False,
                min_score=0.01,
            )
            other_group = memory.search(
                "medical",
                "default",
                "breach liability",
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
