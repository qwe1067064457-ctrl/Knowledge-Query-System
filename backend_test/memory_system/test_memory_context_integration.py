from __future__ import annotations

import asyncio
import unittest

from helpers import (
    TEST_TMP_ROOT,
    make_context_manager,
    make_entry,
    make_memory_system,
    make_session_manager,
    temp_workspace,
    write_group_meta,
)


class MemoryContextIntegrationTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        try:
            TEST_TMP_ROOT.rmdir()
        except OSError:
            pass

    def test_context_manager_injects_core_memory_block(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                sessions = make_session_manager(workspace)
                memory = make_memory_system(workspace)
                context = make_context_manager(workspace)

                session = sessions.create_session("law", "default", "u1")
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

                prepared = await context.prepare(
                    "law",
                    "default",
                    session.id,
                    extra_messages=[{"role": "user", "content": "Explain breach liability."}],
                    query="breach liability",
                    allow_compaction=False,
                )
                joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
                self.assertIn("Default to Chinese output.", joined)
                self.assertIn("In the law group, cite statutes first.", joined)

        asyncio.run(run())

    def test_context_manager_injects_related_memory_block(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                sessions = make_session_manager(workspace)
                memory = make_memory_system(workspace)
                context = make_context_manager(workspace)

                session = sessions.create_session("law", "default", "u1")
                memory.write_daily_log(
                    "law",
                    "default",
                    "Today's discussion connects breach liability with damages.",
                    user_id="u1",
                )
                memory.write_domain_case(
                    group_id="law",
                    title="Breach liability case",
                    content="The case relates breach liability to foreseeability.",
                )

                prepared = await context.prepare(
                    "law",
                    "default",
                    session.id,
                    extra_messages=[{"role": "user", "content": "Continue the breach-liability discussion."}],
                    query="breach liability",
                    allow_compaction=False,
                )
                joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
                self.assertIn("damages", joined)
                self.assertIn("Breach liability case", joined)

        asyncio.run(run())

    def test_prepare_uses_latest_compaction_boundary_and_keeps_memory_injection(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                sessions = make_session_manager(workspace)
                memory = make_memory_system(workspace)
                context = make_context_manager(workspace)

                session = sessions.create_session("law", "default", "u1")
                sessions.append_entry("law", "default", make_entry(session.id, "law", "user", "very old question"))
                sessions.append_entry(
                    "law",
                    "default",
                    make_entry(session.id, "law", "system", "earlier compacted summary", entry_type="compaction"),
                )
                sessions.append_entry("law", "default", make_entry(session.id, "law", "assistant", "answer after compaction"))
                memory.write_daily_log(
                    "law",
                    "default",
                    "Related log: breach liability should be analyzed with damages rules.",
                    user_id="u1",
                )

                prepared = await context.prepare(
                    "law",
                    "default",
                    session.id,
                    extra_messages=[{"role": "user", "content": "Continue discussing breach liability."}],
                    query="breach liability",
                    allow_compaction=False,
                )
                joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
                self.assertIn("earlier compacted summary", joined)
                self.assertIn("damages rules", joined)
                self.assertNotIn("very old question", joined)

        asyncio.run(run())

    def test_flush_from_context_writes_daily_log_for_correct_user_group(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                memory = make_memory_system(workspace)

                result = await memory.flush_from_context(
                    "law",
                    "default",
                    "Recorded: the user confirmed archived sessions still accept writes.",
                    user_id="u1",
                    source_session_id="s1",
                )

                self.assertTrue(result["flushed"])
                rows = memory.get_recent_memories("law", "default", days=1, user_id="u1")
                self.assertEqual(len(rows), 1)
                self.assertIn("archived sessions still accept writes", rows[0].content)
                self.assertEqual(rows[0].user_id, "u1")

        asyncio.run(run())

    def test_flush_from_context_respects_checkpoint_enabled_false(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                write_group_meta(
                    workspace,
                    "law",
                    {
                        "enabled_memory_types": ["core", "daily_log", "domain_case"],
                        "core": {
                            "explicit_markers": ["ALWAYS"],
                            "group_scope_keywords": ["LAW"],
                            "min_candidate_length": 1,
                            "max_candidate_length": 120,
                        },
                        "daily_log": {"checkpoint_enabled": False},
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
                    "This summary would normally be written to the daily log.",
                    user_id="u1",
                    source_session_id="s1",
                )

                self.assertFalse(result["flushed"])
                self.assertEqual(memory.get_recent_memories("law", "default", days=1, user_id="u1"), [])

        asyncio.run(run())

    def test_flush_from_context_promotes_explicit_core_memory_with_scope(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                write_group_meta(
                    workspace,
                    "law",
                    {
                        "enabled_memory_types": ["core", "daily_log", "domain_case"],
                        "core": {
                            "explicit_markers": ["ALWAYS", "DEFAULT"],
                            "group_scope_keywords": ["LAW", "STATUTE"],
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

                await memory.flush_from_context(
                    "law",
                    "default",
                    "Checkpoint summary",
                    user_id="u1",
                    source_session_id="s1",
                    messages=[
                        {"role": "user", "content": "ALWAYS answer in Chinese."},
                        {"role": "user", "content": "DEFAULT in this LAW workspace, cite STATUTE text first."},
                    ],
                )

                results = memory.get_core_memories(user_id="u1", group_id="law")
                payload = {(item.scope, item.content) for item in results}
                self.assertIn(("user_global", "ALWAYS answer in Chinese."), payload)
                self.assertIn(("user_group", "DEFAULT in this LAW workspace, cite STATUTE text first."), payload)

        asyncio.run(run())

    def test_flush_from_context_promotes_structured_domain_case(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                write_group_meta(
                    workspace,
                    "law",
                    {
                        "enabled_memory_types": ["core", "daily_log", "domain_case"],
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

                await memory.flush_from_context(
                    "law",
                    "default",
                    "ISSUE: how to determine breach liability. ANALYSIS: compare damages and foreseeability. CONCLUSION: use statutes and facts together. DONE.",
                    user_id="u1",
                    source_session_id="s1",
                    messages=[
                        {"role": "user", "content": "Please summarize one breach-liability CASE."},
                        {
                            "role": "assistant",
                            "content": "ISSUE: how to determine breach liability. ANALYSIS: compare damages and foreseeability. CONCLUSION: use statutes and facts together. DONE.",
                        },
                    ],
                )

                results = memory.search(
                    "law",
                    "default",
                    "breach liability CASE",
                    user_id="u2",
                    include_core=False,
                    include_daily_logs=False,
                    min_score=0.01,
                )
                self.assertTrue(results)
                self.assertEqual(results[0].memory_type, "domain_case")
                self.assertEqual(results[0].scope, "group_shared")

        asyncio.run(run())

    def test_flush_from_context_does_not_promote_case_without_required_structure(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                write_group_meta(
                    workspace,
                    "law",
                    {
                        "enabled_memory_types": ["core", "daily_log", "domain_case"],
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
                    "DONE. Short answer only.",
                    user_id="u1",
                    source_session_id="s1",
                    messages=[{"role": "assistant", "content": "DONE. Short answer only."}],
                )

                self.assertEqual(result["domain_case_written"], 0)
                results = memory.search(
                    "law",
                    "default",
                    "short answer",
                    user_id="u1",
                    include_core=False,
                    include_daily_logs=False,
                    min_score=0.01,
                )
                self.assertFalse(results)

        asyncio.run(run())

    def test_compaction_flush_persists_daily_log_before_summary_writeback(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                sessions = make_session_manager(workspace)
                memory = make_memory_system(workspace)
                context = make_context_manager(workspace)

                def fake_llm(prompt: str) -> str:
                    if "提取对你主人重要的信息" in prompt:
                        return "- Record: the user confirmed archived sessions still accept writes."
                    return "Compaction summary"

                context.config.memory_flush_enabled = True
                context.set_llm_call(fake_llm)

                session = sessions.create_session("law", "default", "u1")
                for index in range(6):
                    role = "user" if index % 2 == 0 else "assistant"
                    sessions.append_entry(
                        "law",
                        "default",
                        make_entry(
                            session.id,
                            "law",
                            role,
                            "Very long context body " * 40,
                            token_count=120,
                        ),
                    )

                prepared = await context.prepare(
                    "law",
                    "default",
                    session.id,
                    max_turns=20,
                    soft_threshold_tokens=10,
                    keep_recent_tokens=5,
                    allow_compaction=True,
                )

                transcript = sessions.get_transcript("law", "default", session.id)
                compactions = [item for item in transcript if item.entry_type == "compaction"]
                recent_logs = memory.get_recent_memories("law", "default", days=1, user_id="u1")

                self.assertEqual(len(compactions), 1)
                self.assertTrue(recent_logs)
                self.assertIn("archived sessions still accept writes", recent_logs[0].content)
                self.assertIn("Compaction summary", compactions[0].content)
                self.assertIn("compaction", prepared)

        asyncio.run(run())

    @unittest.skip("Enable after the broader core auto-promotion strategy is finalized.")
    def test_core_auto_promotion_todo(self) -> None:
        self.fail("todo")

    @unittest.skip("Enable after the broader domain-case promotion strategy is finalized.")
    def test_domain_case_auto_promotion_todo(self) -> None:
        self.fail("todo")


if __name__ == "__main__":
    unittest.main()
