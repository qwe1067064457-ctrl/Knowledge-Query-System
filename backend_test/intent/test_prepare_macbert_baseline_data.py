from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.prepare_macbert_baseline_data import (
    TASK_SHAPE_LABELS,
    load_training_export,
    prepare_macbert_datasets,
    write_macbert_datasets,
)


def _row(
    *,
    row_id: str,
    split: str,
    user_query: str,
    history: list[dict[str, str]],
    soft_doubt: bool,
    shape: str,
) -> dict:
    return {
        "id": row_id,
        "batch": "test_batch",
        "split": split,
        "input": {
            "user_query": user_query,
            "history": history,
        },
        "evidence": {},
        "resolved": {
            "main_intent": "qa",
            "modifiers": {
                "soft_doubt": soft_doubt,
            },
            "task": {
                "complexity": "simple",
                "shape": shape,
            },
            "context_dependency": "none",
        },
        "control": {"route": "rag", "mode": "normal"},
        "metadata": {
            "source_dataset": "fixture_dataset",
            "label_tier": "gold",
        },
    }


def test_prepare_macbert_datasets_builds_soft_doubt_and_task_shape_outputs() -> None:
    rows = [
        _row(
            row_id="r1",
            split="train",
            user_query="你刚才那个结论是不是过于绝对？",
            history=[{"role": "assistant", "content": "这个结论在所有情况下都成立。"}],
            soft_doubt=True,
            shape="verify",
        ),
        _row(
            row_id="r2",
            split="dev",
            user_query="帮我总结一下要点。",
            history=[],
            soft_doubt=False,
            shape="summarize",
        ),
        _row(
            row_id="r3",
            split="heldout",
            user_query="你好呀",
            history=[],
            soft_doubt=False,
            shape="none",
        ),
    ]

    prepared = prepare_macbert_datasets(rows)

    soft_train = prepared["datasets"]["soft_doubt"]["train"][0]
    assert soft_train["label"] == 1
    assert "[历史]" in soft_train["text"]
    assert "[当前问题]" in soft_train["text"]

    shape_train = prepared["datasets"]["task_shape"]["train"][0]
    assert shape_train["label_name"] == "verify"
    assert shape_train["label"] == TASK_SHAPE_LABELS.index("verify")

    shape_dev = prepared["datasets"]["task_shape"]["dev"][0]
    assert shape_dev["label_name"] == "summarize"

    assert prepared["datasets"]["task_shape"]["heldout"] == []


def test_write_macbert_datasets_writes_split_jsonl_and_manifest(tmp_path: Path) -> None:
    rows = [
        _row(
            row_id="r1",
            split="train",
            user_query="这个是不是还要补证据？",
            history=[],
            soft_doubt=True,
            shape="verify",
        ),
        _row(
            row_id="r2",
            split="heldout",
            user_query="请对比两个方案",
            history=[],
            soft_doubt=False,
            shape="compare",
        ),
    ]
    prepared = prepare_macbert_datasets(rows)

    source_path = tmp_path / "intent_training_fixture.jsonl"
    source_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    write_macbert_datasets(tmp_path / "macbert_ready", prepared, source_path=source_path)

    soft_train = (tmp_path / "macbert_ready" / "soft_doubt" / "train.jsonl").read_text(encoding="utf-8").strip().splitlines()
    shape_heldout = (tmp_path / "macbert_ready" / "task_shape" / "heldout.jsonl").read_text(encoding="utf-8").strip().splitlines()
    manifest = json.loads((tmp_path / "macbert_ready" / "manifest.json").read_text(encoding="utf-8"))

    assert len(soft_train) == 1
    assert len(shape_heldout) == 1
    assert manifest["source_path"].endswith("intent_training_fixture.jsonl")


def test_load_training_export_reads_jsonl_rows(tmp_path: Path) -> None:
    export_path = tmp_path / "export.jsonl"
    export_path.write_text(
        "\n".join(
            [
                json.dumps(_row(row_id="r1", split="train", user_query="A", history=[], soft_doubt=False, shape="single_question"), ensure_ascii=False),
                json.dumps(_row(row_id="r2", split="dev", user_query="B", history=[], soft_doubt=True, shape="verify"), ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_training_export(export_path)

    assert [row["id"] for row in rows] == ["r1", "r2"]
