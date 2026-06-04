from __future__ import annotations

import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.workflow_answer.evaluate_workflow_answer import (
    build_case_from_trace_events,
    evaluate_case,
    evaluate_cases,
    load_cases,
    summarize_results,
    validate_case,
    write_report,
)


@pytest.fixture()
def workspace_tmp_dir() -> Path:
    target = Path(".test_tmp") / "evaluation_workflow_answer" / uuid4().hex
    target.mkdir(parents=True, exist_ok=False)
    return target


def _case(**overrides):
    payload = {
        "case_id": "case_001",
        "trace_id": "trace_001",
        "source": "offline_seed",
        "user_query": "劳动合同试用期最长多久？",
        "knowledge_evidence_summary": {
            "retrieval_quality_status": "good",
            "query_unit_count": 1,
            "merged_evidence_count": 2,
            "source_ref_count": 1,
            "missing_evidence": False,
        },
        "retrieval_summary": {
            "evidence_summary": {
                "retrieval_quality_status": "good",
                "query_unit_count": 1,
                "merged_evidence_count": 2,
                "source_ref_count": 1,
                "missing_evidence": False,
            }
        },
        "workflow_summary": {
            "evidence_summary": {
                "retrieval_quality_status": "good",
                "query_unit_count": 1,
                "merged_evidence_count": 2,
                "source_ref_count": 1,
                "missing_evidence": False,
            }
        },
        "answer_text": "试用期时长与合同期限相关，并不是任意延长。",
        "core_summary_present": True,
        "user_feedback": None,
    }
    payload.update(overrides)
    return payload


def test_validate_case_accepts_complete_case() -> None:
    validate_case(_case())


def test_validate_case_rejects_missing_field() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        validate_case({"case_id": "x"})


def test_build_case_from_trace_events_assembles_minimal_case() -> None:
    events = [
        {
            "event_type": "retrieval_run",
            "trace_id": "trace_build_001",
            "input_summary": {"query": "公司拖欠工资怎么办？"},
            "output_summary": {
                "evidence_summary": {
                    "retrieval_quality_status": "weak",
                    "query_unit_count": 1,
                    "merged_evidence_count": 1,
                    "source_ref_count": 1,
                    "missing_evidence": False,
                }
            },
        },
        {
            "event_type": "answer_model_run",
            "trace_id": "trace_build_001",
            "input_summary": {"messages_summary": {"latest_user_query": "公司拖欠工资怎么办？"}},
            "output_summary": {},
            "metadata": {"memory_block_types": ["[Core Memory]"]},
        },
        {
            "event_type": "workflow_run",
            "trace_id": "trace_build_001",
            "output_summary": {"evidence_summary": {"merged_evidence_count": 1}},
        },
    ]

    case = build_case_from_trace_events(events, answer_text="先收集证据再走投诉或仲裁。")

    assert case["case_id"] == "trace_build_001"
    assert case["source"] == "offline_replay"
    assert case["user_query"] == "公司拖欠工资怎么办？"
    assert case["core_summary_present"] is True
    assert case["knowledge_evidence_summary"]["merged_evidence_count"] == 1


def test_build_case_from_trace_events_rejects_mixed_trace_ids() -> None:
    events = [
        {"event_type": "retrieval_run", "trace_id": "trace_a", "input_summary": {"query": "Q"}},
        {"event_type": "answer_model_run", "trace_id": "trace_b", "output_summary": {}},
    ]

    with pytest.raises(ValueError, match="exactly one trace_id"):
        build_case_from_trace_events(events, answer_text="A")


def test_evaluate_case_keeps_feedback_out_of_score_but_flags_review() -> None:
    case = _case(user_feedback="dislike")
    result = evaluate_case(
        case,
        retrieval_semantic_labels={"relevance": "good", "sufficiency": "good", "usability": "good"},
        answer_semantic_labels={
            "answered": "good",
            "grounded": "good",
            "consistency_with_evidence": "good",
            "constraint_coverage": "good",
            "no_hallucination": "good",
        },
    )

    assert result["answer"]["label"] == "good"
    assert result["answer"]["score"] >= 0.8
    assert result["needs_human_review"] is True
    assert "dislike_high_score" in result["human_review_reasons"]
    assert result["grader_metadata"]["finalize_meta"]["policy"]["mode"] == "parallel_merge"
    assert result["topic"] == "workflow_answer"
    assert result["dimension_labels"] == {"retrieval": "good", "answer": "good"}


def test_evaluate_cases_accepts_offline_and_online_sources() -> None:
    cases = [
        _case(case_id="offline_001", source="offline_seed"),
        _case(case_id="online_001", source="online_sample", user_feedback="like"),
    ]

    results = evaluate_cases(cases)

    assert [item["source"] for item in results] == ["offline_seed", "online_sample"]
    assert all("retrieval" in item and "answer" in item for item in results)


def test_load_cases_reads_jsonl_file(workspace_tmp_dir: Path) -> None:
    path = workspace_tmp_dir / "cases.jsonl"
    rows = [_case(case_id="case_a"), _case(case_id="case_b", trace_id="trace_b")]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    loaded = load_cases(path)

    assert [item["case_id"] for item in loaded] == ["case_a", "case_b"]


def test_summarize_results_and_write_report_support_empty_and_non_empty(workspace_tmp_dir: Path) -> None:
    empty_summary = summarize_results([])
    assert empty_summary["samples"] == 0

    results = [
        evaluate_case(
            _case(case_id="case_summary"),
            retrieval_semantic_labels={"relevance": "good", "sufficiency": "good", "usability": "weak"},
            answer_semantic_labels={
                "answered": "good",
                "grounded": "good",
                "consistency_with_evidence": "good",
                "constraint_coverage": "weak",
                "no_hallucination": "good",
            },
        )
    ]
    summary = summarize_results(results)
    report_dir = workspace_tmp_dir / "report"
    write_report(report_dir, results=results, summary=summary)

    assert summary["samples"] == 1
    assert (report_dir / "results.jsonl").exists()
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "report.md").exists()


def test_evaluate_cases_with_llm_falls_back_to_rules_when_runtime_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from evaluation.workflow_answer import evaluate_workflow_answer as module
    from evaluation.workflow_answer import model_impl

    class BrokenRuntime:
        def grade_case(self, case):
            raise RuntimeError("llm down")

    monkeypatch.setattr(model_impl, "WorkflowAnswerLLMRuntime", BrokenRuntime)

    results = module.evaluate_cases([_case(case_id="runtime_error_case")], use_llm=True)

    assert results[0]["retrieval"]["label"] in {"good", "weak", "bad"}
    assert results[0]["grader_metadata"]["model_result_meta"]["retrieval"]["error"] == "llm down"
    assert results[0]["grader_metadata"]["finalize_meta"]["policy"]["llm_failure_fallback"] == "rule_labels"
