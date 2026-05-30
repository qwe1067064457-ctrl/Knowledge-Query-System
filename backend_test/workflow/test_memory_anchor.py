from __future__ import annotations

from datetime import datetime

from context.models import MemoryEntry, TranscriptEntry
from context.session import DEFAULT_AGENT, SessionManager
from memory_system.context_hydrator import MemoryContextHydrator
from memory_system.memory_anchor import MemoryAnchorBuilder
from workflow.workers.memory_anchor_worker import MemoryAnchorWorker


def test_memory_anchor_marks_hydratable_entry() -> None:
    entry = MemoryEntry(
        content="阶段性摘要",
        source="users/default/groups/law/daily_logs/2026-05-24.jsonl",
        group_id="law",
        timestamp=datetime.now(),
        memory_type="daily_log",
        source_session_id="session_1",
        metadata={"id": "mem_1"},
    )

    anchor = MemoryAnchorBuilder().build(entry)

    assert anchor.can_hydrate_context is True
    assert anchor.source_session_id == "session_1"
    assert anchor.anchor_key == "mem_1"


def test_memory_context_hydrator_returns_empty_without_session_id(tmp_path) -> None:
    manager = SessionManager(tmp_path)
    anchor = MemoryAnchorBuilder().build(
        MemoryEntry(
            content="阶段性摘要",
            source="users/default/groups/law/daily_logs/2026-05-24.jsonl",
            group_id="law",
            timestamp=datetime.now(),
            memory_type="daily_log",
        )
    )

    hydrated = MemoryContextHydrator().hydrate(
        anchor=anchor,
        session_manager=manager,
        group_id="law",
        agent_id=DEFAULT_AGENT,
    )

    assert hydrated == []


def test_memory_context_hydrator_loads_transcript_context(tmp_path) -> None:
    manager = SessionManager(tmp_path)
    session = manager.create_session("law", DEFAULT_AGENT, "user_a")
    manager.append_entry(
        "law",
        DEFAULT_AGENT,
        TranscriptEntry(
            id="entry_1",
            session_id=session.id,
            group_id="law",
            timestamp=1,
            role="user",
            entry_type="normal",
            content="劳动合同法第19条怎么规定？",
        ),
    )
    anchor = MemoryAnchorBuilder().build(
        MemoryEntry(
            content="阶段性摘要",
            source="users/default/groups/law/daily_logs/2026-05-24.jsonl",
            group_id="law",
            timestamp=datetime.now(),
            memory_type="daily_log",
            source_session_id=session.id,
        )
    )

    hydrated = MemoryContextHydrator().hydrate(
        anchor=anchor,
        session_manager=manager,
        group_id="law",
        agent_id=DEFAULT_AGENT,
    )

    assert len(hydrated) == 1
    assert hydrated[0]["content"] == "劳动合同法第19条怎么规定？"


def test_memory_context_hydrator_prefers_anchor_spans_over_full_session(tmp_path) -> None:
    manager = SessionManager(tmp_path)
    session = manager.create_session("law", DEFAULT_AGENT, "user_a")
    for idx, content in enumerate(
        [
            "第一轮背景",
            "第二轮问题",
            "第三轮关键分析",
            "第四轮关键结论",
            "第五轮无关延伸",
        ],
        start=1,
    ):
        manager.append_entry(
            "law",
            DEFAULT_AGENT,
            TranscriptEntry(
                id=f"entry_{idx}",
                session_id=session.id,
                group_id="law",
                timestamp=idx,
                role="assistant" if idx % 2 == 0 else "user",
                entry_type="normal",
                content=content,
            ),
        )
    anchor = MemoryAnchorBuilder().build(
        MemoryEntry(
            content="阶段性摘要",
            source="groups/law/users/user_a/memory/daily_log/2026-05-24.jsonl",
            group_id="law",
            timestamp=datetime.now(),
            memory_type="daily_log",
            source_session_id=session.id,
            anchor_spans=[{"start_entry_id": "entry_3", "end_entry_id": "entry_4", "reason": "关键片段", "confidence": 0.9}],
        )
    )

    hydrated = MemoryContextHydrator().hydrate(
        anchor=anchor,
        session_manager=manager,
        group_id="law",
        agent_id=DEFAULT_AGENT,
        limit=4,
    )

    contents = [item["content"] for item in hydrated]
    assert "第三轮关键分析" in contents
    assert "第四轮关键结论" in contents
    assert "第五轮无关延伸" not in contents


def test_memory_anchor_worker_builds_anchor_without_faking_context() -> None:
    worker = MemoryAnchorWorker()
    entry = MemoryEntry(
        content="阶段性摘要",
        source="users/default/groups/law/daily_logs/2026-05-24.jsonl",
        group_id="law",
        timestamp=datetime.now(),
        memory_type="daily_log",
    )

    anchor = worker.build_anchor(entry)

    assert anchor.can_hydrate_context is False
    assert anchor.source_session_id is None
