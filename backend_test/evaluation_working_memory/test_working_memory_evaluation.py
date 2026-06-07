from __future__ import annotations

import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.working_memory.evaluate_working_memory import (
    evaluate_case,
    evaluate_cases,
    load_cases,
    validate_case,
    write_report,
)
from evaluation.working_memory.topic_config import summarize_results


@pytest.fixture()
def workspace_tmp_dir() -> Path:
    target = Path(".test_tmp") / "evaluation_working_memory" / uuid4().hex
    target.mkdir(parents=True, exist_ok=False)
    return target


def _case(**overrides):
    payload = {
        "case_id": "wm_case_001",
        "trace_id": "trace_wm_001",
        "source": "offline_seed",
        "working_memory_summary": {
            "entries": [
                {"entry_type": "focus_task", "content": "核验劳动合同试用期上限"},
                {"entry_type": "resolved_query", "content": "用户实际在问试用期与合同期限关系"},
                {"entry_type": "review_outcome", "content": "上一轮确认需要看劳动法"},
            ],
            "head": {
                "active_entry_ids": ["1", "2", "3"],
                "current_focus_task_ids": ["1"],
                "latest_resolved_query_id": "2",
                "latest_review_outcome_id": "3",
            },
            "active_entry_count": 3,
            "noise_entry_count": 0,
            "stale_entry_count": 0,
        },
        "expected_focus_task_present": True,
        "expected_resolved_query_present": True,
        "expected_review_outcome_present": True,
        "expected_handoff_ready": True,
        "user_feedback": None,
    }
    payload.update(overrides)
    return payload


def test_validate_case_accepts_complete_case() -> None:
    validate_case(_case())


def test_validate_case_rejects_missing_field() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        validate_case({"case_id": "x"})


def test_evaluate_case_scores_positive_working_memory_case() -> None:
    result = evaluate_case(
        _case(),
        semantic_labels={
            "continuity_support": "good",
            "key_state_capture": "good",
            "noise_control": "good",
            "freshness": "good",
            "handoff_utility": "good",
        },
    )

    assert result["topic"] == "working_memory"
    assert result["label"] == "good"
    assert result["score"] >= 0.8


def test_evaluate_case_flags_missing_key_state_bad_case() -> None:
    result = evaluate_case(
        _case(
            working_memory_summary={
                "entries": [
                    {"entry_type": "answer_unit", "content": "旧总结"},
                    {"entry_type": "answer_unit", "content": "无关闲聊"},
                ],
                "head": {
                    "active_entry_ids": ["1", "2"],
                    "current_focus_task_ids": [],
                    "latest_resolved_query_id": None,
                    "latest_review_outcome_id": None,
                },
                "active_entry_count": 2,
                "noise_entry_count": 2,
                "stale_entry_count": 1,
            },
            expected_review_outcome_present=False,
            user_feedback="dislike",
        )
    )

    assert result["label"] == "bad"
    assert "missing_focus_task" in result["reasons"]
    assert "missing_resolved_query" in result["reasons"]
    assert "too_noisy" in result["reasons"]
    assert result["needs_human_review"] is True


def test_load_cases_and_write_report_roundtrip(workspace_tmp_dir: Path) -> None:
    path = workspace_tmp_dir / "cases.jsonl"
    rows = [_case(case_id="a"), _case(case_id="b", trace_id="trace_b")]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    loaded = load_cases(path)
    results = evaluate_cases(loaded)
    summary = summarize_results(results)
    report_dir = workspace_tmp_dir / "report"
    write_report(report_dir, results=results, summary=summary)

    assert [item["case_id"] for item in loaded] == ["a", "b"]
    assert (report_dir / "results.jsonl").exists()
    assert (report_dir / "summary.json").exists()
    assert (report_dir / "report.md").exists()


def test_evaluate_cases_with_llm_falls_back_to_rules_when_runtime_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from evaluation.working_memory import evaluate_working_memory as module
    from evaluation.working_memory.graders.model_layer import model_evaluator

    class BrokenRuntime:
        def grade_case(self, case):
            raise RuntimeError("llm down")

    monkeypatch.setattr(model_evaluator, "WorkingMemoryLLMRuntime", BrokenRuntime)

    results = module.evaluate_cases([_case(case_id="runtime_error_case")], use_llm=True)

    assert results[0]["label"] in {"good", "weak", "bad"}
    assert results[0]["grader_metadata"]["model_result_meta"]["error"] == "llm down"
    assert results[0]["grader_metadata"]["finalize_meta"]["policy"]["llm_failure_fallback"] == "rule_labels"
