from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent import export_intent_training_set as export_module
from evaluation.intent.export_intent_training_set import export_training_rows, write_training_jsonl


def _dataset_row(*, row_id: str, batch: str, complexity: str = "simple") -> dict:
    return {
        "id": row_id,
        "batch": batch,
        "input": {
            "user_query": "测试 query",
            "history": [],
        },
        "gold": {
            "evidence": {
                "classifier_mode": "rule_plus_model",
                "required_signals": ["qa"],
                "required_rule_ids": [],
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
                    "needs_clarification": False,
                    "out_of_scope": False,
                    "soft_doubt": False,
                },
                "task": {
                    "complexity": complexity,
                    "shape": "single_question",
                },
                "context_dependency": "none",
            },
            "control": {
                "route": "rag",
                "mode": "normal",
            },
        },
        "source_query_id": row_id,
    }


def test_export_training_rows_marks_train_and_heldout_splits(tmp_path: Path) -> None:
    train_dir = tmp_path / "train_dataset"
    dev_dir = tmp_path / "dev_dataset"
    heldout_dir = tmp_path / "heldout_dataset"
    train_dir.mkdir()
    dev_dir.mkdir()
    heldout_dir.mkdir()
    (train_dir / "rows.json").write_text(json.dumps([_dataset_row(row_id="train_001", batch="standard_qa")], ensure_ascii=False), encoding="utf-8")
    (dev_dir / "rows.json").write_text(json.dumps([_dataset_row(row_id="dev_001", batch="standard_qa")], ensure_ascii=False), encoding="utf-8")
    (heldout_dir / "rows.json").write_text(json.dumps([_dataset_row(row_id="heldout_001", batch="qa_judgment_heldout")], ensure_ascii=False), encoding="utf-8")

    exported = export_training_rows(
        train_dataset_dirs=[train_dir],
        dev_dataset_dirs=[dev_dir],
        heldout_dataset_dirs=[heldout_dir],
    )

    assert len(exported) == 3
    assert {row["split"] for row in exported} == {"train", "dev", "heldout"}
    assert {row["metadata"]["is_heldout"] for row in exported} == {False, True}


def test_export_training_rows_infers_difficulty_and_preserves_gold_layers(tmp_path: Path) -> None:
    train_dir = tmp_path / "train_dataset"
    train_dir.mkdir()
    (train_dir / "rows.json").write_text(
        json.dumps(
            [
                _dataset_row(row_id="complex_001", batch="mixed_intent", complexity="complex"),
                _dataset_row(row_id="simple_001", batch="standard_qa", complexity="simple"),
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exported = export_training_rows(train_dataset_dirs=[train_dir], heldout_dataset_dirs=[])

    by_id = {row["id"]: row for row in exported}
    assert by_id["complex_001"]["metadata"]["difficulty"] == "hard"
    assert by_id["simple_001"]["metadata"]["difficulty"] == "easy"
    assert by_id["simple_001"]["resolved"]["main_intent"] == "qa"
    assert by_id["simple_001"]["control"]["route"] == "rag"


def test_export_training_rows_keeps_other_default_splits_when_only_train_is_overridden(tmp_path: Path) -> None:
    train_dir = tmp_path / "train_dataset"
    default_dev_dir = tmp_path / "default_dev_dataset"
    default_heldout_dir = tmp_path / "default_heldout_dataset"
    default_silver_dir = tmp_path / "default_silver_dataset"
    for path in (train_dir, default_dev_dir, default_heldout_dir, default_silver_dir):
        path.mkdir()

    (train_dir / "rows.json").write_text(
        json.dumps([_dataset_row(row_id="train_001", batch="standard_qa")], ensure_ascii=False),
        encoding="utf-8",
    )
    (default_dev_dir / "rows.json").write_text(
        json.dumps([_dataset_row(row_id="dev_001", batch="standard_qa")], ensure_ascii=False),
        encoding="utf-8",
    )
    (default_heldout_dir / "rows.json").write_text(
        json.dumps([_dataset_row(row_id="heldout_001", batch="qa_judgment_heldout")], ensure_ascii=False),
        encoding="utf-8",
    )
    (default_silver_dir / "rows.json").write_text(
        json.dumps([_dataset_row(row_id="silver_001", batch="follow_up")], ensure_ascii=False),
        encoding="utf-8",
    )

    original_dev_dirs = export_module.DEFAULT_DEV_DATASET_DIRS
    original_heldout_dirs = export_module.DEFAULT_HELDOUT_DATASET_DIRS
    original_silver_root = export_module.DEFAULT_SILVER_DATASET_ROOT
    try:
        export_module.DEFAULT_DEV_DATASET_DIRS = (default_dev_dir,)
        export_module.DEFAULT_HELDOUT_DATASET_DIRS = (default_heldout_dir,)
        export_module.DEFAULT_SILVER_DATASET_ROOT = tmp_path

        exported = export_training_rows(train_dataset_dirs=[train_dir])
    finally:
        export_module.DEFAULT_DEV_DATASET_DIRS = original_dev_dirs
        export_module.DEFAULT_HELDOUT_DATASET_DIRS = original_heldout_dirs
        export_module.DEFAULT_SILVER_DATASET_ROOT = original_silver_root

    assert {row["split"] for row in exported} == {"train", "dev", "heldout"}
    assert {row["id"] for row in exported} == {"train_001", "dev_001", "heldout_001", "silver_001"}
    by_id = {row["id"]: row for row in exported}
    assert by_id["silver_001"]["split"] == "train"
    assert by_id["heldout_001"]["metadata"]["is_heldout"] is True


def test_write_training_jsonl_writes_one_row_per_line(tmp_path: Path) -> None:
    rows = [
        {
            "id": "row_001",
            "batch": "standard_qa",
            "split": "train",
            "input": {"user_query": "测试", "history": []},
            "evidence": {"rule_expectations": {}},
            "resolved": {"main_intent": "qa"},
            "control": {"route": "rag"},
            "metadata": {"source_dataset": "demo", "is_heldout": False},
        },
        {
            "id": "row_002",
            "batch": "heldout",
            "split": "heldout",
            "input": {"user_query": "测试2", "history": []},
            "evidence": {"rule_expectations": {}},
            "resolved": {"main_intent": "qa"},
            "control": {"route": "rag"},
            "metadata": {"source_dataset": "demo2", "is_heldout": True},
        },
    ]
    output_path = tmp_path / "intent_training.jsonl"

    write_training_jsonl(output_path, rows)

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == "row_001"
    assert json.loads(lines[1])["metadata"]["is_heldout"] is True
