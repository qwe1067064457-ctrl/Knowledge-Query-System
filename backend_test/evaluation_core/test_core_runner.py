from __future__ import annotations

import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.core.case_loader import load_jsonl_cases
from evaluation.core.report_writer import StandardReportWriter
from evaluation.core.runner import TopicRunnerConfig, evaluate_topic_cases, run_topic_evaluation


@pytest.fixture()
def workspace_tmp_dir() -> Path:
    target = Path(".test_tmp") / "evaluation_core" / uuid4().hex
    target.mkdir(parents=True, exist_ok=False)
    return target


def test_load_jsonl_cases_supports_file_and_directory(workspace_tmp_dir: Path) -> None:
    case_a = {"case_id": "a", "trace_id": "trace_a", "source": "offline_seed"}
    case_b = {"case_id": "b", "trace_id": "trace_b", "source": "online_sample"}
    file_a = workspace_tmp_dir / "a.jsonl"
    file_b = workspace_tmp_dir / "b.jsonl"
    file_a.write_text(json.dumps(case_a, ensure_ascii=False) + "\n", encoding="utf-8")
    file_b.write_text(json.dumps(case_b, ensure_ascii=False) + "\n", encoding="utf-8")

    from_file = load_jsonl_cases(file_a)
    from_dir = load_jsonl_cases(workspace_tmp_dir)

    assert [item["case_id"] for item in from_file] == ["a"]
    assert [item["case_id"] for item in from_dir] == ["a", "b"]


def test_evaluate_topic_cases_runs_rule_model_finalize_and_report(workspace_tmp_dir: Path) -> None:
    events: list[str] = []

    class StubRuleEvaluator:
        def evaluate(self, case):
            events.append(f"rule:{case['case_id']}")
            return {"labels": {"quality": "weak"}, "metadata": {"owner": "rule"}}

    class StubModelEvaluator:
        def evaluate(self, case):
            events.append(f"model:{case['case_id']}")
            return {"labels": {"quality": "good"}, "metadata": {"owner": "model"}}

    class StubFinalizer:
        def finalize(self, case, *, rule_result, model_result):
            events.append(f"finalize:{case['case_id']}")
            return {
                "case_id": case["case_id"],
                "trace_id": case["trace_id"],
                "source": case["source"],
                "topic": case["topic"],
                "dimension_labels": {"quality": model_result["labels"]["quality"]},
                "dimension_scores": {"quality": 1.0},
                "score": 1.0,
                "label": "good",
                "reasons": [],
                "grader_metadata": {
                    "rule_result_meta": rule_result,
                    "model_result_meta": model_result,
                    "finalize_meta": {"fallback_applied": False},
                },
                "needs_human_review": False,
                "human_review_reasons": [],
                "review_priority": "normal",
            }

    writer = StandardReportWriter(
        summary_builder=lambda rows: {"samples": len(list(rows))},
        markdown_builder=lambda summary: f"# Samples\n\n- samples: {summary['samples']}\n",
    )
    config = TopicRunnerConfig(
        topic="stub_topic",
        rule_evaluator=StubRuleEvaluator(),
        model_evaluator=StubModelEvaluator(),
        finalizer=StubFinalizer(),
        report_writer=writer,
    )
    cases_path = workspace_tmp_dir / "cases.jsonl"
    cases_path.write_text(
        json.dumps({"case_id": "case_1", "trace_id": "trace_1", "source": "offline_seed"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    results, summary = run_topic_evaluation(cases_path, config=config, report_dir=workspace_tmp_dir / "report")

    assert events == ["rule:case_1", "model:case_1", "finalize:case_1"]
    assert results[0]["topic"] == "stub_topic"
    assert summary["samples"] == 1
    assert (workspace_tmp_dir / "report" / "results.jsonl").exists()
    assert (workspace_tmp_dir / "report" / "summary.json").exists()
    assert (workspace_tmp_dir / "report" / "report.md").exists()


def test_evaluate_topic_cases_supports_model_absence_with_finalize_fallback() -> None:
    class StubRuleEvaluator:
        def evaluate(self, case):
            return {"labels": {"quality": "weak"}, "metadata": {"owner": "rule"}}

    class StubFinalizer:
        def finalize(self, case, *, rule_result, model_result):
            chosen_label = rule_result["labels"]["quality"] if model_result is None else model_result["labels"]["quality"]
            return {
                "case_id": case["case_id"],
                "trace_id": case["trace_id"],
                "source": case["source"],
                "topic": case["topic"],
                "dimension_labels": {"quality": chosen_label},
                "dimension_scores": {"quality": 0.5},
                "score": 0.5,
                "label": chosen_label,
                "reasons": ["rule_fallback"] if model_result is None else [],
                "grader_metadata": {"finalize_meta": {"fallback_applied": model_result is None}},
                "needs_human_review": False,
                "human_review_reasons": [],
                "review_priority": "normal",
            }

    writer = StandardReportWriter(
        summary_builder=lambda rows: {"samples": len(list(rows))},
        markdown_builder=lambda summary: "# Summary\n",
    )
    config = TopicRunnerConfig(
        topic="stub_topic",
        rule_evaluator=StubRuleEvaluator(),
        model_evaluator=None,
        finalizer=StubFinalizer(),
        report_writer=writer,
    )

    results = evaluate_topic_cases([{"case_id": "x", "trace_id": "t", "source": "offline_seed"}], config=config)

    assert results[0]["label"] == "weak"
    assert results[0]["reasons"] == ["rule_fallback"]
    assert results[0]["grader_metadata"]["finalize_meta"]["fallback_applied"] is True
