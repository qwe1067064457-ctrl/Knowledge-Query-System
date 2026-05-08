from __future__ import annotations

import asyncio
import shutil
import time
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from context.context_manager import ContextManager
from context.dataclasses import TranscriptEntry
from context.legacy_adapter import DEFAULT_AGENT, DEFAULT_GROUP, LegacySessionManagerAdapter
from context.memory_system import MemorySystem
from context.session_manager import SessionManager


TEST_TMP_ROOT = Path(__file__).resolve().parent / ".test_tmp"


@contextmanager
def temp_workspace() -> Iterator[str]:
    TEST_TMP_ROOT.mkdir(exist_ok=True)
    path = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


def entry(
    session_id: str,
    group_id: str,
    role: str,
    content: str,
    entry_type: str = "normal",
    token_count: int | None = None,
) -> TranscriptEntry:
    return TranscriptEntry(
        id=f"entry_{time.time_ns()}",
        session_id=session_id,
        group_id=group_id,
        timestamp=int(time.time() * 1000),
        role=role,
        entry_type=entry_type,
        content=content,
        token_count=token_count,
    )


class ContextModuleTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        try:
            TEST_TMP_ROOT.rmdir()
        except OSError:
            pass

    def test_session_storage_is_group_isolated(self) -> None:
        with temp_workspace() as tmp:
            manager = SessionManager(Path(tmp) / "storage")

            general = manager.create_session(
                "general",
                "default",
                "user-a",
                metadata={"title": "通用会话"},
            )
            legal = manager.create_session("legal", "legal_agent", "user-a")

            manager.append_entry(
                "general",
                "default",
                entry(general.id, "general", "user", "通用问题"),
            )
            manager.append_entry(
                "legal",
                "legal_agent",
                entry(legal.id, "legal", "user", "法律问题"),
            )

            self.assertEqual(
                len(manager.get_transcript("general", "default", general.id)),
                1,
            )
            self.assertEqual(
                len(manager.get_transcript("legal", "legal_agent", legal.id)),
                1,
            )
            self.assertEqual(
                manager.list_user_sessions("general", "default", "user-a")[0].metadata,
                {"title": "通用会话"},
            )
            with self.assertRaises(ValueError):
                manager.create_session("../bad", "default", "user-a")

    def test_memory_search_handles_chinese_terms(self) -> None:
        with temp_workspace() as tmp:
            memory = MemorySystem(Path(tmp) / "storage")
            memory.write_to_long_term(
                "legal",
                "legal_agent",
                "用户偏好：回答违约责任问题时需要引用民法典法条。",
            )

            results = memory.search(
                "legal",
                "legal_agent",
                "违约责任 民法典",
                top_k=3,
                min_score=0.01,
            )

            self.assertTrue(results)
            self.assertIn("违约责任", results[0].content)

    def test_legacy_adapter_normalizes_frontend_tool_calls(self) -> None:
        with temp_workspace() as tmp:
            storage = Path(tmp) / "storage"
            manager = SessionManager(storage)
            adapter = LegacySessionManagerAdapter(manager)
            adapter.configure_legacy_paths(Path(tmp))
            session = adapter.create_session("工具会话")

            adapter.save_message(
                session["id"],
                "assistant",
                "已读取文件。",
                tool_calls=[
                    {
                        "tool": "read_file",
                        "input": "knowledge/example.md",
                        "output": "example",
                    }
                ],
            )

            entries = manager.get_transcript(
                DEFAULT_GROUP,
                DEFAULT_AGENT,
                session["id"],
            )

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].tool_calls[0].function["name"], "read_file")
            self.assertEqual(
                entries[0].tool_calls[0].function["arguments"],
                "knowledge/example.md",
            )

    def test_prepare_uses_latest_compaction_boundary_and_injects_memory(self) -> None:
        async def run() -> None:
            with temp_workspace() as tmp:
                storage = Path(tmp) / "storage"
                sessions = SessionManager(storage)
                memory = MemorySystem(storage)
                context = ContextManager(sessions, memory)

                session = sessions.create_session("legal", "legal_agent", "user-a")
                sessions.append_entry(
                    "legal",
                    "legal_agent",
                    entry(session.id, "legal", "user", "很早之前的问题"),
                )
                sessions.append_entry(
                    "legal",
                    "legal_agent",
                    entry(
                        session.id,
                        "legal",
                        "system",
                        "较早对话摘要",
                        entry_type="compaction",
                    ),
                )
                sessions.append_entry(
                    "legal",
                    "legal_agent",
                    entry(session.id, "legal", "assistant", "压缩后的回答"),
                )
                memory.write_to_long_term(
                    "legal",
                    "legal_agent",
                    "违约责任回答需要说明损失赔偿和可预见规则。",
                )

                prepared = await context.prepare(
                    "legal",
                    "legal_agent",
                    session.id,
                    extra_messages=[{"role": "user", "content": "继续讲违约责任"}],
                    query="违约责任",
                    allow_compaction=False,
                )
                joined = "\n".join(
                    str(message.get("content", "")) for message in prepared["messages"]
                )

                self.assertIn("较早对话摘要", joined)
                self.assertIn("相关记忆", joined)
                self.assertIn("压缩后的回答", joined)
                self.assertIn("继续讲违约责任", joined)
                self.assertNotIn("很早之前的问题", joined)

        asyncio.run(run())

    def test_prepare_compacts_once_without_recursing_forever(self) -> None:
        async def run() -> None:
            with temp_workspace() as tmp:
                storage = Path(tmp) / "storage"
                sessions = SessionManager(storage)
                memory = MemorySystem(storage)
                context = ContextManager(sessions, memory)
                context.config.memory_flush_enabled = False
                context.set_llm_call(lambda _: "压缩摘要")

                session = sessions.create_session("general", "default", "user-a")
                for index in range(6):
                    sessions.append_entry(
                        "general",
                        "default",
                        entry(
                            session.id,
                            "general",
                            "user" if index % 2 == 0 else "assistant",
                            "很长的上下文内容" * 50,
                            token_count=100,
                        ),
                    )

                prepared = await context.prepare(
                    "general",
                    "default",
                    session.id,
                    max_turns=20,
                    soft_threshold_tokens=10,
                    keep_recent_tokens=5,
                    allow_compaction=True,
                )
                compactions = [
                    item
                    for item in sessions.get_transcript("general", "default", session.id)
                    if item.entry_type == "compaction"
                ]

                self.assertEqual(len(compactions), 1)
                self.assertIn("压缩摘要", prepared["messages"][0]["content"])

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
