from __future__ import annotations

from memory_system.session_working_memory.models import SessionWorkingMemory, WorkingMemoryEntry, WorkingMemoryHead
from memory_system.session_working_memory.writer import SessionWorkingMemoryWriter
from workflow.powers.challenge_power import ChallengePower
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.types import EvidenceBundle, EvidenceItem
from workflow.workers.binding_worker import BindingWorker
from workflow.workers.review_worker import ReviewWorker


def _working_memory(*entries: WorkingMemoryEntry) -> SessionWorkingMemory:
    return SessionWorkingMemory(
        entries=list(entries),
        head=WorkingMemoryHead(active_entry_ids=[entry.entry_id for entry in entries]),
    )


class _FakeRetrievalPower:
    def retrieve(self, query_units, *, top_k: int = 4, path_filters=()) -> EvidenceBundle:
        del top_k
        del path_filters
        return EvidenceBundle(
            query_unit_results=tuple(
                {
                    "unit_id": unit.unit_id,
                    "query": unit.text,
                    "origin": unit.origin,
                }
                for unit in query_units
            ),
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="evidence_thread_2",
                    source_path="notes/thread.md",
                    source_type="official_structured",
                    locator="challenge-contract",
                    snippet="ChallengePower 还未完全统一进 Context Binding V2 contract。",
                    channel="vector",
                    score=0.88,
                    query_unit_ids=tuple(unit.unit_id for unit in query_units),
                ),
            ),
            source_refs=("notes/thread.md",),
            coverage_summary={"query_units": len(query_units), "sources": 1},
            quality_summary={"average_weighted_score": 0.88},
            missing_evidence_notes=(),
        )


def test_thread_goal_writer_keeps_high_value_entries_from_dialogue_like_turn() -> None:
    writer = SessionWorkingMemoryWriter()

    entries = writer.build_entries_from_turn(
        turn_id="turn_thread_18",
        user_query="你刚才那个说法有问题，而且 challenge 还没完全统一。",
        answer_text=(
            "第一点：context binding 不是唯一 referent 恢复器。"
            "第二点：ChallengePower 还没完全统一进同一套 contract。"
        ),
        current_goal="验证 context binding 在近20轮真实对话里的表现。",
        binding_result={
            "rewritten_query": "ChallengePower 为什么还没完全统一进 Context Binding V2 contract",
            "resolved_target_ids": ["wm_answer_challenge_contract"],
            "binding_confidence": "high",
        },
        review_result={"status": "partial_success", "summary": "challenge contract 仍需统一"},
    )

    types = {entry.entry_type for entry in entries}

    assert "focus_task" in types
    assert "resolved_query" in types
    assert "answer_unit" in types
    assert "user_assertion" in types
    assert "review_outcome" in types


def test_thread_goal_writer_does_not_store_weak_small_talk_as_answer_unit_or_assertion() -> None:
    writer = SessionWorkingMemoryWriter()

    entries = writer.build_entries_from_turn(
        turn_id="turn_thread_smalltalk",
        user_query="好的，继续。",
        answer_text="嗯，我们接着看。",
    )

    assert entries == []


def test_thread_goal_followup_challenge_uses_llm_after_relevant_set_filtering() -> None:
    power = ContextBindingPower()
    memory = _working_memory(
        WorkingMemoryEntry(
            entry_id="wm_answer_binding_role",
            entry_type="answer_unit",
            turn_id="turn_thread_12",
            source_kind="answer",
            source_ref="turn_thread_12:answer:1",
            content="context binding 不是唯一 referent 恢复器，而是按需触发的 query rewrite / context resolution。",
            structured_payload={"unit_index": 1},
            confidence="high",
        ),
        WorkingMemoryEntry(
            entry_id="wm_answer_challenge_contract",
            entry_type="answer_unit",
            turn_id="turn_thread_16",
            source_kind="answer",
            source_ref="turn_thread_16:answer:2",
            content="ChallengePower 还没完全统一进 Context Binding V2 contract。",
            structured_payload={"unit_index": 2},
            confidence="high",
        ),
        WorkingMemoryEntry(
            entry_id="wm_review_contract_gap",
            entry_type="review_outcome",
            turn_id="turn_thread_17",
            source_kind="review",
            source_ref="turn_thread_17:review",
            content="challenge 目标恢复与 context binding resolution 仍未完全统一。",
            confidence="high",
        ),
    )

    def fake_llm_call(prompt: str) -> str:
        assert "候选相关对象" in prompt
        return '{"resolved_target_ids":["wm_answer_challenge_contract"],"rewritten_query":"ChallengePower 为什么还没完全统一进 Context Binding V2 contract","confidence":"high","needs_clarification":false,"fallback_type":null,"reason":null}'

    result = power.bind(
        "你刚才说 challenge 还没完全统一，这个具体指什么？",
        [],
        working_memory=memory,
        recent_messages=[
            {"role": "assistant", "content": "ChallengePower 还没完全统一进 Context Binding V2 contract。"},
            {"role": "user", "content": "那这是什么意思？"},
        ],
        llm_call=fake_llm_call,
        rewrite_query=True,
    )

    assert result.matched_by == "llm_resolution"
    assert result.resolved_target_ids == ("wm_answer_challenge_contract",)
    assert result.rewritten_query == "ChallengePower 为什么还没完全统一进 Context Binding V2 contract"
    assert result.binding_snapshot["relevant_set_size"] >= 1


def test_thread_goal_pure_ambiguity_returns_clarification_fallback() -> None:
    power = ContextBindingPower()
    memory = _working_memory(
        WorkingMemoryEntry(
            entry_id="wm_answer_one",
            entry_type="answer_unit",
            turn_id="turn_thread_10",
            source_kind="answer",
            source_ref="turn_thread_10:answer:1",
            content="relevant set 还是规则第一版。",
            structured_payload={"unit_index": 1},
            confidence="high",
        ),
        WorkingMemoryEntry(
            entry_id="wm_answer_two",
            entry_type="answer_unit",
            turn_id="turn_thread_11",
            source_kind="answer",
            source_ref="turn_thread_11:answer:1",
            content="working memory writer 仍然偏粗。",
            structured_payload={"unit_index": 1},
            confidence="high",
        ),
    )

    def fake_llm_call(prompt: str) -> str:
        assert "候选相关对象" in prompt
        return '{"resolved_target_ids":[],"rewritten_query":"","confidence":"low","needs_clarification":true,"fallback_type":"needs_clarification","reason":"multiple_relevant_targets"}'

    result = power.bind(
        "这个呢？",
        [],
        working_memory=memory,
        recent_messages=[{"role": "user", "content": "我们刚才讨论了 relevant set 和 writer。"}],
        llm_call=fake_llm_call,
        rewrite_query=True,
    )

    assert result.needs_clarification is True
    assert result.fallback_type == "needs_clarification"
    assert result.reason == "multiple_relevant_targets"
    assert len(result.relevant_set) >= 2


def test_thread_goal_challenge_prefers_existing_evidence_before_follow_up_retrieval() -> None:
    power = ChallengePower()

    result = power.execute(
        query="你刚才说 challenge 还没完全统一，这个依据是什么？",
        candidate_targets=[
            {
                "object_id": "wm_answer_challenge_contract",
                "object_type": "answer_unit",
                "content": "ChallengePower 还没完全统一进 Context Binding V2 contract。",
                "refs": ["evidence_thread_1"],
            }
        ],
        evidence_candidates=[
            {
                "object_id": "evidence_thread_1",
                "object_type": "evidence_ref",
                "content": "challenge 会先消费 binding contract，再看 existing evidence 是否足够。",
                "refs": ["evidence_thread_1"],
            }
        ],
        binding_worker=BindingWorker(),
        review_worker=ReviewWorker(),
        retrieval_power=_FakeRetrievalPower(),
    )

    assert result.status == "success"
    assert result.evidence_assessment["sufficient"] is True
    assert result.evidence_assessment["triggered_additional_retrieval"] is False
    assert result.review_findings[0]["judgment"] == "supported"
