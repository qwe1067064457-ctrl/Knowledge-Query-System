from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.annotate_v2_samples import (
    annotate_dataset_rows,
    run_annotation,
    summarize_annotated_rows,
)


def _row(
    *,
    row_id: str,
    query: str,
    complexity: str = "simple",
    shape: str = "single_question",
    route: str = "rag",
    mode: str = "normal",
    needs_clarification: bool = False,
) -> dict:
    return {
        "id": row_id,
        "batch": "test_batch",
        "input": {
            "user_query": query,
            "history": [],
        },
        "gold": {
            "evidence": {
                "classifier_mode": "rule_plus_model",
                "required_signals": ["qa"],
                "required_rule_ids": ["intent.qa.generic"],
                "rule_expectations": {"intent.qa.generic": True},
                "unsupported_signals": {
                    "file_write_request": False,
                    "file_delete_request": False,
                    "kb_admin_request": False,
                    "privileged_operation": False,
                    "unknown_external_action": False,
                },
                "dependency_signals": {
                    "none": True,
                    "history_reference": False,
                    "previous_answer": False,
                    "previous_retrieval": False,
                    "ambiguous": False,
                },
            },
            "resolved": {
                "main_intent": "qa",
                "modifiers": {
                    "follow_up": False,
                    "challenge": False,
                    "ask_source": False,
                    "ask_capability": False,
                    "needs_clarification": needs_clarification,
                    "out_of_scope": False,
                    "soft_doubt": False,
                },
                "task": {
                    "complexity": complexity,
                    "shape": shape,
                },
                "context_dependency": "none",
            },
            "control": {
                "route": route,
                "mode": mode,
            },
        },
        "notes": "test seed",
        "source_query_id": row_id,
    }


def test_annotate_dataset_rows_marks_changed_parallel_subtask_rows_for_review() -> None:
    rows = [
        _row(
            row_id="parallel_001",
            query="请分别说明试用期的条件、流程、时限。",
            complexity="simple",
            shape="single_question",
        )
    ]

    annotated = annotate_dataset_rows(rows, dataset_name="demo_dataset")

    assert annotated[0]["gold"]["resolved"]["task"]["complexity"] == "compound"
    assert annotated[0]["gold"]["resolved"]["task"]["topology"] == "parallel_subtasks"
    assert annotated[0]["migration_review"]["required"] is True
    assert "changed_resolved_task_complexity" in annotated[0]["migration_review"]["reasons"]
    assert annotated[0]["comparison"]["has_changes"] is True


def test_annotate_dataset_rows_keeps_stable_simple_rows_without_review_flag() -> None:
    rows = [
        _row(
            row_id="stable_001",
            query="合同违约后通常可以主张哪些救济方式？",
            complexity="simple",
            shape="single_question",
        )
    ]

    annotated = annotate_dataset_rows(rows, dataset_name="demo_dataset")

    assert annotated[0]["gold"]["resolved"]["task"]["complexity"] == "simple"
    assert annotated[0]["gold"]["resolved"]["task"]["topology"] == "single"
    assert annotated[0]["migration_review"]["required"] is False
    assert annotated[0]["comparison"]["has_changes"] is False


def test_run_annotation_writes_all_rows_and_summary(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "demo_dataset"
    dataset_dir.mkdir()
    rows = [
        _row(
            row_id="parallel_001",
            query="请分别说明试用期的条件、流程、时限。",
            complexity="simple",
            shape="single_question",
        ),
        _row(
            row_id="stable_001",
            query="合同违约后通常可以主张哪些救济方式？",
            complexity="simple",
            shape="single_question",
        ),
    ]
    (dataset_dir / "rows.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    summary_rows = run_annotation(dataset_dirs=[dataset_dir], output_dir=tmp_path / "out")

    assert summary_rows[0]["total"] == 2
    assert summary_rows[0]["review_required"] == 1

    written_rows = (tmp_path / "out" / "demo_dataset.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(written_rows) == 2
    written_summary = json.loads((tmp_path / "out" / "summary.json").read_text(encoding="utf-8"))
    assert written_summary[0]["changed_rows"] == 1


def test_summarize_annotated_rows_counts_changed_fields_and_review_reasons() -> None:
    annotated_rows = [
        {
            "comparison": {
                "has_changes": True,
                "changed_fields": ["resolved.task.complexity", "resolved.task.topology"],
            },
            "migration_review": {
                "required": True,
                "reasons": ["changed_resolved.task.complexity"],
            },
        },
        {
            "comparison": {
                "has_changes": False,
                "changed_fields": [],
            },
            "migration_review": {
                "required": False,
                "reasons": [],
            },
        },
    ]

    summary = summarize_annotated_rows(annotated_rows)

    assert summary["total"] == 2
    assert summary["changed_rows"] == 1
    assert summary["review_required"] == 1
    assert summary["changed_field_counts"]["resolved.task.complexity"] == 1
