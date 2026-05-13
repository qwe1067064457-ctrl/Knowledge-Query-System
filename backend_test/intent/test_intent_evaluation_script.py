from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.evaluate_intent_rules import evaluate_dataset, load_dataset


def _row(
    *,
    row_id: str,
    batch: str,
    query: str,
    main_intent: str,
    route: str,
    mode: str,
    rule_expectations: dict[str, bool],
) -> dict:
    return {
        "id": row_id,
        "batch": batch,
        "input": {
            "user_query": query,
            "history": [],
        },
        "gold": {
            "evidence": {
                "classifier_mode": "rule_plus_model",
                "required_signals": ["qa"] if main_intent == "qa" else ["chat"],
                "required_rule_ids": [],
                "rule_expectations": rule_expectations,
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
                "main_intent": main_intent,
                "modifiers": {
                    "follow_up": False,
                    "challenge": False,
                    "ask_source": False,
                    "ask_capability": False,
                    "needs_clarification": False,
                    "out_of_scope": False,
                },
                "task": {
                    "complexity": "simple",
                    "shape": "single_question" if main_intent == "qa" else "none",
                },
                "context_dependency": "none",
            },
            "control": {
                "route": route,
                "mode": mode,
            },
        },
        "notes": "test row",
    }


def test_load_dataset_reads_all_json_rows(tmp_path: Path) -> None:
    rows_a = [_row(
        row_id="a1",
        batch="standard_qa",
        query="劳动合同试用期最长多久？",
        main_intent="qa",
        route="rag",
        mode="normal",
        rule_expectations={"intent.qa.domain": True},
    )]
    rows_b = [_row(
        row_id="b1",
        batch="chat",
        query="你好",
        main_intent="chat",
        route="chat",
        mode="normal",
        rule_expectations={"intent.chat.greeting": True},
    )]
    (tmp_path / "a.json").write_text(json.dumps(rows_a, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(rows_b, ensure_ascii=False), encoding="utf-8")

    rows = load_dataset(tmp_path)

    assert len(rows) == 2
    assert {row["id"] for row in rows} == {"a1", "b1"}


def test_evaluate_dataset_returns_expected_metric_sections(tmp_path: Path) -> None:
    rows = [
        _row(
            row_id="a1",
            batch="standard_qa",
            query="劳动合同试用期最长多久？",
            main_intent="qa",
            route="rag",
            mode="normal",
            rule_expectations={"intent.qa.domain": True, "intent.chat.greeting": False},
        ),
        _row(
            row_id="a2",
            batch="chat",
            query="你好",
            main_intent="chat",
            route="chat",
            mode="normal",
            rule_expectations={"intent.chat.greeting": True, "intent.qa.domain": False},
        ),
    ]

    summary = evaluate_dataset(rows)

    assert summary["overall"]["samples"] == 2
    assert "per_batch" in summary
    assert "rule_stats" in summary
    assert summary["overall"]["resolved_main_intent_accuracy"] >= 0.5
    assert "intent.qa.domain" in summary["rule_stats"]


def test_evaluate_dataset_detects_mislabeled_row(tmp_path: Path) -> None:
    rows = [
        _row(
            row_id="m1",
            batch="chat",
            query="你好",
            main_intent="qa",
            route="rag",
            mode="normal",
            rule_expectations={"intent.qa.domain": True, "intent.chat.greeting": False},
        )
    ]

    summary = evaluate_dataset(rows)

    assert summary["overall"]["samples"] == 1
    assert summary["overall"]["resolved_main_intent_accuracy"] == 0.0
    assert summary["overall"]["control_route_accuracy"] == 0.0
