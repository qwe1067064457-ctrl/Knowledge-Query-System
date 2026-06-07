from __future__ import annotations

from workflow.workers.binding_worker import BindingWorker


def _candidate(object_id: str, object_type: str, content: str, confidence: str = "high") -> dict:
    return {
        "object_id": object_id,
        "object_type": object_type,
        "content": content,
        "confidence": confidence,
        "status": "active",
    }


def test_filter_relevant_set_prioritizes_answer_units_for_assertion_like_queries() -> None:
    worker = BindingWorker()
    candidates = [
        _candidate("question_1", "question_object", "这个问题怎么拆？"),
        _candidate("answer_1", "answer_unit", "这个结论是试用期上限一个月。"),
        _candidate("assertion_1", "user_assertion", "你刚才的说法需要再确认。"),
    ]

    result = worker.filter_relevant_set(
        query="这个结论的依据是什么？",
        candidates=candidates,
        query_style="challenge",
    )

    object_types = {item["object_type"] for item in result["relevant_set"]}
    assert object_types == {"answer_unit", "user_assertion"}
    assert "question_object" not in object_types


def test_filter_relevant_set_prioritizes_review_outcome_for_review_queries() -> None:
    worker = BindingWorker()
    candidates = [
        _candidate("review_1", "review_outcome", "上次评估状态是证据不足。"),
        _candidate("answer_1", "answer_unit", "这个结论是试用期上限一个月。"),
        _candidate("question_1", "question_object", "这个问题怎么拆？"),
    ]

    result = worker.filter_relevant_set(
        query="这个评估为什么判成证据不足？",
        candidates=candidates,
        query_style="challenge",
    )

    relevant = list(result["relevant_set"])
    assert relevant[0]["object_type"] == "review_outcome"
    assert all(item["object_type"] in {"review_outcome", "answer_unit"} for item in relevant)


def test_filter_relevant_set_prioritizes_question_objects_for_task_queries() -> None:
    worker = BindingWorker()
    candidates = [
        _candidate("answer_1", "answer_unit", "这个结论是试用期上限一个月。"),
        _candidate("focus_1", "focus_task", "比较试用期规则和竞业限制规则。"),
        _candidate("question_1", "question_object", "这个问题要怎么拆成执行单元？"),
    ]

    result = worker.filter_relevant_set(
        query="这个问题要怎么拆成几个步骤？",
        candidates=candidates,
        query_style="follow_up",
    )

    object_types = {item["object_type"] for item in result["relevant_set"]}
    assert "answer_unit" not in object_types
    assert object_types == {"focus_task", "question_object"}


def test_filter_relevant_set_keeps_candidates_when_no_explicit_cue_matches() -> None:
    worker = BindingWorker()
    candidates = [
        _candidate("resolved_1", "resolved_query", "一年期劳动合同试用期上限是多少？"),
        _candidate("focus_1", "focus_task", "劳动合同试用期规则检索。"),
    ]

    result = worker.filter_relevant_set(
        query="一年期劳动合同试用期上限是多少？",
        candidates=candidates,
        query_style="standalone",
    )

    assert len(result["relevant_set"]) == 2
    assert {item["object_type"] for item in result["relevant_set"]} == {"resolved_query", "focus_task"}
