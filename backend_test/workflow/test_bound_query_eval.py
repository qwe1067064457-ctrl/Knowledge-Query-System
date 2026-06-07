from __future__ import annotations

from memory_system.session_working_memory.models import SessionWorkingMemory, WorkingMemoryEntry, WorkingMemoryHead
from workflow.helpers.bound_query_eval_helper import (
    BoundQueryEvalCase,
    evaluate_bound_query_case,
    summarize_bound_query_outcomes,
)
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.types import ContextBindingResult


def _working_memory(*entries: WorkingMemoryEntry) -> SessionWorkingMemory:
    return SessionWorkingMemory(
        entries=list(entries),
        head=WorkingMemoryHead(active_entry_ids=[entry.entry_id for entry in entries]),
    )


def _fake_llm_call(prompt: str) -> str:
    return (
        '{"resolved_target_ids":["question_2"],"rewritten_query":"Dell XPS 14 重量多少？",'
        '"confidence":"high","needs_clarification":false,"fallback_type":null,"reason":null}'
    )


def test_bound_query_short_followup_eval_suite_reports_precision_and_rates() -> None:
    power = ContextBindingPower()
    cases = [
        {
            "eval": BoundQueryEvalCase(
                case_id="llm_rewrite",
                query="那它的重量呢？",
                expected_mode="auto_bind",
                expected_target_ids=("question_2",),
                expected_rewritten_query="Dell XPS 14 重量多少？",
            ),
            "bind": {
                "query": "那它的重量呢？",
                "candidates": [
                    {"object_id": "question_1", "object_type": "question_object", "content": "MacBook Pro M3 重量多少？", "source_power": "workflow"},
                    {"object_id": "question_2", "object_type": "question_object", "content": "Dell XPS 14 重量多少？", "source_power": "workflow"},
                ],
                "recent_messages": [
                    {"role": "user", "content": "MacBook Pro M3 重量多少？"},
                    {"role": "assistant", "content": "1.6kg"},
                    {"role": "user", "content": "那 Dell XPS 14 呢？"},
                ],
                "llm_call": _fake_llm_call,
                "rewrite_query": True,
            },
        },
        {
            "eval": BoundQueryEvalCase(
                case_id="multi_target_rule",
                query="前两个结论的依据都对吗？",
                expected_mode="clarify",
            ),
            "bind": {
                "query": "前两个结论的依据都对吗？",
                "candidates": [],
                "working_memory": _working_memory(
                    WorkingMemoryEntry(
                        entry_id="wm_answer_1",
                        entry_type="answer_unit",
                        turn_id="turn_1",
                        source_kind="answer",
                        source_ref="turn_1:answer:1",
                        content="第一点：第一个结论的依据是什么？",
                        structured_payload={"unit_index": 1, "refs": ["evidence_1"]},
                        confidence="high",
                    ),
                    WorkingMemoryEntry(
                        entry_id="wm_answer_2",
                        entry_type="answer_unit",
                        turn_id="turn_1",
                        source_kind="answer",
                        source_ref="turn_1:answer:2",
                        content="第二点：第二个结论的依据是什么？",
                        structured_payload={"unit_index": 2, "refs": ["evidence_2"]},
                        confidence="high",
                    ),
                    WorkingMemoryEntry(
                        entry_id="wm_answer_3",
                        entry_type="answer_unit",
                        turn_id="turn_1",
                        source_kind="answer",
                        source_ref="turn_1:answer:3",
                        content="第三点：第三个结论的依据是什么？",
                        structured_payload={"unit_index": 3, "refs": ["evidence_3"]},
                        confidence="high",
                    ),
                ),
            },
        },
        {
            "eval": BoundQueryEvalCase(
                case_id="no_candidates_clarify",
                query="这个是什么意思",
                expected_mode="clarify",
            ),
            "bind": {
                "query": "这个是什么意思",
                "candidates": [],
            },
        },
        {
            "eval": BoundQueryEvalCase(
                case_id="vague_followup_clarify",
                query="这个还有吗",
                expected_mode="clarify",
            ),
            "bind": {
                "query": "这个还有吗",
                "candidates": [
                    {"object_id": "question_1", "object_type": "question_object", "content": "第一个问题", "source_power": "workflow"},
                    {"object_id": "question_2", "object_type": "question_object", "content": "第二个问题", "source_power": "workflow"},
                ],
            },
        },
    ]

    outcomes = []
    for case in cases:
        result = power.bind(**case["bind"])
        outcomes.append(evaluate_bound_query_case(case["eval"], result))

    summary = summarize_bound_query_outcomes(outcomes)

    assert summary["total_cases"] == 4
    assert summary["auto_bind_count"] == 1
    assert summary["clarification_count"] == 3
    assert summary["auto_bind_precision"] == 1.0
    assert summary["clarification_rate"] == 0.75
    assert summary["misbind_rate"] == 0.0
    assert summary["correct_case_rate"] == 1.0


def test_bound_query_eval_summary_marks_misbinds_explicitly() -> None:
    case = BoundQueryEvalCase(
        case_id="misbind_case",
        query="它的依据是什么",
        expected_mode="auto_bind",
        expected_target_ids=("question_2",),
    )
    result = ContextBindingResult(
        bound_targets=(
            {"object_id": "question_1", "object_type": "question_object", "content": "第一个问题"},
        ),
        binding_confidence="high",
        matched_by="rule_binding",
    )

    outcome = evaluate_bound_query_case(case, result)
    summary = summarize_bound_query_outcomes([outcome])

    assert outcome.is_correct is False
    assert outcome.is_misbind is True
    assert summary["misbind_count"] == 1
    assert summary["misbind_rate"] == 1.0
