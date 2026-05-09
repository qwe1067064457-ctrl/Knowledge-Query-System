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
                    content="默认中文输出。",
                )
                memory.write_core_memory(
                    user_id="u1",
                    group_id="law",
                    scope="user_group",
                    content="法律组优先引用法条。",
                )

                prepared = await context.prepare(
                    "law",
                    "default",
                    session.id,
                    extra_messages=[{"role": "user", "content": "解释违约责任"}],
                    query="违约责任",
                    allow_compaction=False,
                )
                joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
                self.assertIn("核心记忆", joined)
                self.assertIn("默认中文输出。", joined)
                self.assertIn("法律组优先引用法条。", joined)

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
                    "今天确认违约责任需要结合损失赔偿。",
                    user_id="u1",
                )
                memory.write_domain_case(
                    group_id="law",
                    title="违约责任案例",
                    content="案例指出违约责任与可预见规则相关。",
                )

                prepared = await context.prepare(
                    "law",
                    "default",
                    session.id,
                    extra_messages=[{"role": "user", "content": "继续讨论违约责任"}],
                    query="违约责任",
                    allow_compaction=False,
                )
                joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
                self.assertIn("相关记忆", joined)
                self.assertIn("损失赔偿", joined)
                self.assertIn("违约责任案例", joined)

        asyncio.run(run())

    def test_prepare_uses_latest_compaction_boundary_and_keeps_memory_injection(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                sessions = make_session_manager(workspace)
                memory = make_memory_system(workspace)
                context = make_context_manager(workspace)

                session = sessions.create_session("law", "default", "u1")
                sessions.append_entry("law", "default", make_entry(session.id, "law", "user", "很早之前的问题"))
                sessions.append_entry(
                    "law",
                    "default",
                    make_entry(
                        session.id,
                        "law",
                        "system",
                        "较早对话摘要",
                        entry_type="compaction",
                    ),
                )
                sessions.append_entry("law", "default", make_entry(session.id, "law", "assistant", "压缩后的回答"))
                memory.write_daily_log(
                    "law",
                    "default",
                    "相关日志：违约责任应结合赔偿规则。",
                    user_id="u1",
                )

                prepared = await context.prepare(
                    "law",
                    "default",
                    session.id,
                    extra_messages=[{"role": "user", "content": "继续讲违约责任"}],
                    query="违约责任",
                    allow_compaction=False,
                )
                joined = "\n".join(str(item.get("content", "")) for item in prepared["messages"])
                self.assertIn("较早对话摘要", joined)
                self.assertIn("相关记忆", joined)
                self.assertIn("赔偿规则", joined)
                self.assertNotIn("很早之前的问题", joined)

        asyncio.run(run())

    def test_flush_from_context_writes_daily_log_for_correct_user_group(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                memory = make_memory_system(workspace)

                result = await memory.flush_from_context(
                    "law",
                    "default",
                    "- 记录：用户确认 archive 仍可写入",
                    user_id="u1",
                    source_session_id="s1",
                )

                self.assertTrue(result["flushed"])
                rows = memory.get_recent_memories("law", "default", days=1, user_id="u1")
                self.assertEqual(len(rows), 1)
                self.assertIn("archive 仍可写入", rows[0].content)
                self.assertEqual(rows[0].user_id, "u1")

        asyncio.run(run())

    def test_flush_from_context_promotes_explicit_core_memory_with_scope(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                memory = make_memory_system(workspace)

                await memory.flush_from_context(
                    "law",
                    "default",
                    "- 记录：已形成长期偏好",
                    user_id="u1",
                    source_session_id="s1",
                    messages=[
                        {"role": "user", "content": "以后默认中文输出。"},
                        {"role": "user", "content": "法律组后续都优先引用法条。"},
                    ],
                )

                results = memory.get_core_memories(user_id="u1", group_id="law")
                payload = {(item.scope, item.content) for item in results}
                self.assertIn(("user_global", "以后默认中文输出"), payload)
                self.assertIn(("user_group", "法律组后续都优先引用法条"), payload)

        asyncio.run(run())

    def test_flush_from_context_promotes_structured_domain_case(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                memory = make_memory_system(workspace)

                await memory.flush_from_context(
                    "law",
                    "default",
                    "问题：违约责任如何认定。分析：结合损失赔偿和可预见规则。结论：建议按法条和事实分别论证，已完成。",
                    user_id="u1",
                    source_session_id="s1",
                    messages=[
                        {"role": "user", "content": "请总结一个违约责任案例"},
                        {"role": "assistant", "content": "问题：违约责任如何认定。分析：结合损失赔偿和可预见规则。结论：建议按法条和事实分别论证，已完成。"},
                    ],
                )

                results = memory.search(
                    "law",
                    "default",
                    "违约责任 案例",
                    user_id="u2",
                    include_core=False,
                    include_daily_logs=False,
                    min_score=0.01,
                )
                self.assertTrue(results)
                self.assertEqual(results[0].memory_type, "domain_case")
                self.assertEqual(results[0].scope, "group_shared")

        asyncio.run(run())

    def test_compaction_flush_persists_daily_log_before_summary_writeback(self) -> None:
        async def run() -> None:
            with temp_workspace() as workspace:
                sessions = make_session_manager(workspace)
                memory = make_memory_system(workspace)
                context = make_context_manager(workspace)

                def fake_llm(prompt: str) -> str:
                    if "提取对你主人重要的信息" in prompt:
                        return "- 记录：用户确认 archive 仍可写入"
                    return "压缩摘要"

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
                            "很长的上下文内容" * 40,
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
                self.assertIn("archive 仍可写入", recent_logs[0].content)
                self.assertIn("压缩摘要", compactions[0].content)
                self.assertIn("compaction", prepared)

        asyncio.run(run())

    @unittest.skip("待 core 自动晋升策略定稿后启用")
    def test_core_auto_promotion_todo(self) -> None:
        self.fail("todo")

    @unittest.skip("待 domain_case 自动沉淀策略定稿后启用")
    def test_domain_case_auto_promotion_todo(self) -> None:
        self.fail("todo")


if __name__ == "__main__":
    unittest.main()
