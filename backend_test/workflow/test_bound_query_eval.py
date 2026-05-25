from __future__ import annotations

from context.models import SessionDialogueState
from workflow.helpers.bound_query_eval_helper import (
    BoundQueryEvalCase,
    evaluate_bound_query_case,
    summarize_bound_query_outcomes,
)
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.types import ContextBindingResult


def _fake_llm_call(prompt: str) -> str:
    if "上一轮状态" in prompt:
        return (
            '{"focus_question_object_id":"question_2","focus_question_object_text":"Dell XPS 14 重量多少？",'
            '"focus_predicate":"重量","recent_question_objects":[{"object_id":"question_1","content":"MacBook Pro M3 重量多少？"},'
            '{"object_id":"question_2","content":"Dell XPS 14 重量多少？"}],"recent_evidence_topics":[],'
            '"resolution_confidence":"medium","last_update_reason":"llm_state_update"}'
        )
    return (
        '{"resolved_target_ids":["question_2"],"rewritten_query":"Dell XPS 14 重量多少？",'
        '"confidence":"high","needs_clarification":false}'
    )


def test_bound_query_short_followup_eval_suite_reports_precision_and_rates() -> None:
    power = ContextBindingPower()
    cases = [
        {
            "eval": BoundQueryEvalCase(
                case_id="focus_continuity",
                query="你刚才说的这个依据是什么",
                expected_mode="auto_bind",
                expected_target_ids=("question_2",),
            ),
            "bind": {
                "query": "你刚才说的这个依据是什么",
                "candidates": [
                    {"object_id": "question_1", "object_type": "question_object", "content": "旧问题", "source_power": "workflow"},
                    {"object_id": "question_2", "object_type": "question_object", "content": "最新问题", "source_power": "workflow"},
                ],
                "dialogue_state": SessionDialogueState(
                    focus_question_object_id="question_2",
                    focus_question_object_text="最新问题",
                    resolution_confidence="high",
                ),
            },
        },
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
                expected_mode="auto_bind",
                expected_target_ids=("question_1", "question_2"),
            ),
            "bind": {
                "query": "前两个结论的依据都对吗？",
                "candidates": [
                    {"object_id": "question_1", "object_type": "question_object", "content": "第一个结论的依据是什么？", "source_power": "workflow"},
                    {"object_id": "question_2", "object_type": "question_object", "content": "第二个结论的依据是什么？", "source_power": "workflow"},
                    {"object_id": "question_3", "object_type": "question_object", "content": "第三个结论的依据是什么？", "source_power": "workflow"},
                ],
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

    assert summary["total_cases"] == 5
    assert summary["auto_bind_count"] == 3
    assert summary["clarification_count"] == 2
    assert summary["auto_bind_precision"] == 1.0
    assert summary["clarification_rate"] == 0.4
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
