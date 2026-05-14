from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.evaluate_intent_rules import (
    build_rule_supervision_rows_from_dataset,
    evaluate_dataset,
    load_dataset,
    load_rule_supervision,
)


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


def test_load_rule_supervision_filters_to_approved_rows(tmp_path: Path) -> None:
    entries = [
        {
            "id": "generic_001",
            "batch": "standard_qa",
            "input": {"user_query": "如果公司拖欠工资，我可以怎么处理？", "history": []},
            "target_rule_id": "intent.qa.generic",
            "expected": True,
            "review_status": "approved",
        },
        {
            "id": "generic_002",
            "batch": "chat_meta_boundary",
            "input": {"user_query": "最近感觉事情越来越复杂。", "history": []},
            "target_rule_id": "intent.qa.generic",
            "expected": False,
            "review_status": "todo",
        },
        {
            "id": "soft_doubt_001",
            "batch": "challenge",
            "input": {
                "user_query": "这个说法是不是太绝对了？",
                "history": [{"role": "assistant", "content": "这种情况一定要赔偿。"}],
            },
            "target_rule_id": "challenge.soft_doubt",
            "expected": True,
            "review_status": "approved_with_note",
        },
    ]
    path = tmp_path / "rule_supervision.jsonl"
    path.write_text("\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries), encoding="utf-8")

    supervision = load_rule_supervision(path)

    assert len(supervision) == 2
    assert {entry["id"] for entry in supervision} == {"generic_001", "soft_doubt_001"}


def test_evaluate_dataset_includes_external_rule_supervision_without_changing_overall_counts(tmp_path: Path) -> None:
    rows = [
        _row(
            row_id="a1",
            batch="chat",
            query="你好",
            main_intent="chat",
            route="chat",
            mode="normal",
            rule_expectations={"intent.chat.greeting": True},
        )
    ]
    supervision = [
        {
            "id": "generic_001",
            "batch": "standard_qa",
            "input": {"user_query": "如果公司拖欠工资，我可以怎么处理？", "history": []},
            "target_rule_id": "intent.qa.generic",
            "expected": True,
            "review_status": "approved",
        },
        {
            "id": "generic_002",
            "batch": "chat_meta_boundary",
            "input": {"user_query": "最近感觉事情越来越复杂。", "history": []},
            "target_rule_id": "intent.qa.generic",
            "expected": False,
            "review_status": "approved",
        },
    ]

    summary = evaluate_dataset(rows, rule_supervision_rows=supervision)

    assert summary["overall"]["samples"] == 1
    assert summary["rule_stats"]["intent.qa.generic"]["labeled_samples"] == 2
    assert summary["rule_stats"]["intent.qa.generic"]["expected_positive"] == 1
    assert summary["rule_stats"]["intent.qa.generic"]["expected_negative"] == 1


def test_build_rule_supervision_rows_from_dataset_flattens_rule_expectations() -> None:
    dataset_rows = [
        _row(
            row_id="seed_qa_001",
            batch="seed_batch",
            query="这类情况通常会有什么后果？",
            main_intent="qa",
            route="rag",
            mode="normal",
            rule_expectations={
                "intent.qa.generic": True,
                "intent.qa.judgment": False,
            },
        )
    ]

    flattened = build_rule_supervision_rows_from_dataset(
        dataset_rows,
        reviewer="gold_dataset",
        notes_prefix="imported from dataset",
    )

    assert len(flattened) == 2
    assert {entry["target_rule_id"] for entry in flattened} == {
        "intent.qa.generic",
        "intent.qa.judgment",
    }
    assert all(entry["review_status"] == "approved" for entry in flattened)
    assert flattened[0]["id"].startswith("seed_qa_001__")
