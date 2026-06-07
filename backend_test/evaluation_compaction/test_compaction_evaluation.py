from __future__ import annotations

import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.compaction.evaluate_compaction import evaluate_case, evaluate_cases, load_cases, validate_case, write_report
from evaluation.compaction.topic_config import summarize_results


@pytest.fixture()
def workspace_tmp_dir() -> Path:
    target = Path(".test_tmp") / "evaluation_compaction" / uuid4().hex
    target.mkdir(parents=True, exist_ok=False)
    return target


def _case(**overrides):
    payload = {
        "case_id": "comp_case_001",
        "trace_id": "trace_comp_001",
        "source": "offline_seed",
        "pre_compaction_summary": {"fact_count": 4, "has_anchor": True},
        "post_compaction_summary": {
            "key_info_preserved": True,
            "anchor_recoverable": True,
            "sufficient_for_judgement": True,
        },
        "pre_compaction_extraction_summary": {"coverage_status": "good", "coverage_complete": True},
        "expected_anchor_required": True,
        "user_feedback": None,
    }
    payload.update(overrides)
    return payload


def test_validate_case_accepts_complete_case() -> None:
    validate_case(_case())


def test_validate_case_rejects_missing_field() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        validate_case({"case_id": "x"})


def test_evaluate_case_scores_positive_compaction_case() -> None:
    result = evaluate_case(
        _case(),
        semantic_labels={
            "key_info_preserved": "good",
            "anchor_recoverability": "good",
            "post_compaction_sufficiency": "good",
            "pre_compaction_extraction_coverage": "good",
        },
    )

    assert result["topic"] == "compaction"
    assert result["label"] == "good"
    assert result["score"] >= 0.8


def test_evaluate_case_flags_lost_context_bad_case() -> None:
    result = evaluate_case(
        _case(
            post_compaction_summary={
                "key_info_preserved": False,
                "anchor_recoverable": False,
                "sufficient_for_judgement": False,
            },
            pre_compaction_extraction_summary={"coverage_status": "bad", "coverage_complete": False},
            user_feedback="dislike",
        )
    )

    assert result["label"] == "bad"
    assert "lost_key_info" in result["reasons"]
    assert "lost_anchor" in result["reasons"]
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
    from evaluation.compaction import evaluate_compaction as module
    from evaluation.compaction.graders.model_layer import model_evaluator

    class BrokenRuntime:
        def grade_case(self, case):
            raise RuntimeError("llm down")

    monkeypatch.setattr(model_evaluator, "CompactionLLMRuntime", BrokenRuntime)

    results = module.evaluate_cases([_case(case_id="runtime_error_case")], use_llm=True)

    assert results[0]["label"] in {"good", "weak", "bad"}
    assert results[0]["grader_metadata"]["model_result_meta"]["error"] == "llm down"
    assert results[0]["grader_metadata"]["finalize_meta"]["policy"]["llm_failure_fallback"] == "rule_labels"
