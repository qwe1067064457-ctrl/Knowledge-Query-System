from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.prepare_macbert_baseline_data import (
    TASK_SHAPE_LABELS,
    TASK_TOPOLOGY_LABELS,
    TASK_COMPLEXITY_LABELS,
    MAIN_INTENT_LABELS,
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
    main_intent: str,
    complexity: str,
    shape: str,
    topology: str,
    modifiers: dict[str, bool],
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
            "main_intent": main_intent,
            "modifiers": modifiers,
            "task": {
                "complexity": complexity,
                "shape": shape,
                "topology": topology,
            },
            "context_dependency": "none",
        },
        "control": {"route": "rag", "mode": "normal"},
        "metadata": {
            "source_dataset": "fixture_dataset",
            "label_tier": "gold",
        },
    }


def test_prepare_macbert_datasets_builds_binary_and_multiclass_outputs() -> None:
    rows = [
        _row(
            row_id="r1",
            split="train",
            user_query="你刚才那个结论是不是过于绝对？",
            history=[{"role": "assistant", "content": "这个结论在所有情况下都成立。"}],
            main_intent="qa",
            complexity="compound",
            shape="verify",
            topology="parallel_queries",
            modifiers={
                "follow_up": True,
                "challenge": True,
                "soft_doubt": True,
                "ask_source": False,
                "ask_capability": False,
                "needs_clarification": False,
                "out_of_scope": False,
            },
        ),
        _row(
            row_id="r2",
            split="dev",
            user_query="帮我总结一下要点。",
            history=[],
            main_intent="chat",
            complexity="complex",
            shape="summarize",
            topology="staged",
            modifiers={
                "follow_up": False,
                "challenge": False,
                "soft_doubt": False,
                "ask_source": False,
                "ask_capability": True,
                "needs_clarification": False,
                "out_of_scope": False,
            },
        ),
        _row(
            row_id="r3",
            split="heldout",
            user_query="你好",
            history=[],
            main_intent="unsupported",
            complexity="simple",
            shape="none",
            topology="single",
            modifiers={
                "follow_up": False,
                "challenge": False,
                "soft_doubt": False,
                "ask_source": False,
                "ask_capability": False,
                "needs_clarification": True,
                "out_of_scope": True,
            },
        ),
    ]

    prepared = prepare_macbert_datasets(rows)

    soft_train = prepared["datasets"]["soft_doubt"]["train"][0]
    assert soft_train["label"] == 1
    assert "[历史]" in soft_train["text"]
    assert "[当前问题]" in soft_train["text"]

    follow_up_train = prepared["datasets"]["modifier_follow_up"]["train"][0]
    assert follow_up_train["label_name"] == "true"

    intent_dev = prepared["datasets"]["main_intent"]["dev"][0]
    assert intent_dev["label"] == MAIN_INTENT_LABELS.index("chat")

    complexity_train = prepared["datasets"]["task_complexity"]["train"][0]
    assert complexity_train["label"] == TASK_COMPLEXITY_LABELS.index("compound")

    shape_train = prepared["datasets"]["task_shape"]["train"][0]
    assert shape_train["label_name"] == "verify"
    assert shape_train["label"] == TASK_SHAPE_LABELS.index("verify")

    topology_dev = prepared["datasets"]["task_topology"]["dev"][0]
    assert topology_dev["label_name"] == "staged"
    assert topology_dev["label"] == TASK_TOPOLOGY_LABELS.index("staged")


def test_write_macbert_datasets_writes_new_task_dirs_and_manifest(tmp_path: Path) -> None:
    rows = [
        _row(
            row_id="r1",
            split="train",
            user_query="这个是不是还要补证据？",
            history=[],
            main_intent="qa",
            complexity="simple",
            shape="verify",
            topology="single",
            modifiers={
                "follow_up": False,
                "challenge": False,
                "soft_doubt": True,
                "ask_source": True,
                "ask_capability": False,
                "needs_clarification": False,
                "out_of_scope": False,
            },
        ),
        _row(
            row_id="r2",
            split="heldout",
            user_query="请对比两个方案",
            history=[],
            main_intent="qa",
            complexity="complex",
            shape="compare",
            topology="staged",
            modifiers={
                "follow_up": False,
                "challenge": False,
                "soft_doubt": False,
                "ask_source": False,
                "ask_capability": False,
                "needs_clarification": False,
                "out_of_scope": False,
            },
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
    compare_heldout = (tmp_path / "macbert_ready" / "task_shape" / "heldout.jsonl").read_text(encoding="utf-8").strip().splitlines()
    topology_heldout = (tmp_path / "macbert_ready" / "task_topology" / "heldout.jsonl").read_text(encoding="utf-8").strip().splitlines()
    manifest = json.loads((tmp_path / "macbert_ready" / "manifest.json").read_text(encoding="utf-8"))

    assert len(soft_train) == 1
    assert len(compare_heldout) == 1
    assert len(topology_heldout) == 1
    assert "main_intent" in manifest["tasks"]
    assert manifest["source_path"].endswith("intent_training_fixture.jsonl")


def test_load_training_export_reads_jsonl_rows(tmp_path: Path) -> None:
    export_path = tmp_path / "export.jsonl"
    export_path.write_text(
        "\n".join(
            [
                json.dumps(
                    _row(
                        row_id="r1",
                        split="train",
                        user_query="A",
                        history=[],
                        main_intent="qa",
                        complexity="simple",
                        shape="single_question",
                        topology="single",
                        modifiers={
                            "follow_up": False,
                            "challenge": False,
                            "soft_doubt": False,
                            "ask_source": False,
                            "ask_capability": False,
                            "needs_clarification": False,
                            "out_of_scope": False,
                        },
                    ),
                    ensure_ascii=False,
                ),
                json.dumps(
                    _row(
                        row_id="r2",
                        split="dev",
                        user_query="B",
                        history=[],
                        main_intent="chat",
                        complexity="complex",
                        shape="verify",
                        topology="staged",
                        modifiers={
                            "follow_up": False,
                            "challenge": True,
                            "soft_doubt": True,
                            "ask_source": False,
                            "ask_capability": False,
                            "needs_clarification": False,
                            "out_of_scope": False,
                        },
                    ),
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_training_export(export_path)

    assert [row["id"] for row in rows] == ["r1", "r2"]
