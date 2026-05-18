from __future__ import annotations

import json
from pathlib import Path

import pytest

from intent.sft.v2.v2_data import export_v2_rows, load_v2_bundle, summarize_v2_bundle, write_v2_bundle
from intent.sft.v2.v2_eval import (
    apply_multilabel_thresholds,
    choose_multilabel_thresholds,
    compute_multiclass_metrics,
    compute_multilabel_metrics,
)
from intent.sft.v2.v2_label_spaces import MULTICLASS_HEADS, MULTILABEL_HEADS, build_label_space_manifest
from intent.sft.v2.v2_train_multitask import main as train_main


def _v2_export_row(
    *,
    row_id: str,
    split: str,
    main_intent: str = "qa",
    task_complexity: str = "simple",
    task_shape: str = "single_question",
    task_topology: str = "single",
    modifiers: dict[str, bool] | None = None,
    context_signals: dict[str, bool] | None = None,
    safety_bucket: list[str] | None = None,
) -> dict:
    return {
        "id": row_id,
        "split": split,
        "input": {
            "user_query": f"query:{row_id}",
            "history": [{"role": "assistant", "content": "前文"}],
        },
        "evidence": {
            "signal_buckets": {
                "intent": [main_intent] if main_intent in {"qa", "chat", "system"} else [],
                "task": [],
                "context": [],
                "safety": safety_bucket or [],
            },
            "context_signals": {
                "history_reference": bool((context_signals or {}).get("history_reference", False)),
                "previous_answer": bool((context_signals or {}).get("needs_previous_answer", False)),
                "previous_retrieval": bool((context_signals or {}).get("previous_retrieval", False)),
                "clarify_hint": bool((context_signals or {}).get("clarify_hint", False)),
                "ambiguous": bool((context_signals or {}).get("clarify_hint", False)),
            },
        },
        "resolved": {
            "main_intent": main_intent,
            "modifiers": {
                "follow_up": False,
                "challenge": False,
                "soft_doubt": False,
                "ask_source": False,
                "ask_capability": False,
                "needs_clarification": False,
                "out_of_scope": False,
                **(modifiers or {}),
            },
            "task": {
                "complexity": task_complexity,
                "shape": task_shape,
                "topology": task_topology,
            },
            "context_dependency": "none",
        },
        "control": {"route": "rag", "mode": "normal"},
        "metadata": {
            "source_dataset": "fixture",
            "label_tier": "gold",
            "is_heldout": split == "heldout",
        },
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_build_label_space_manifest_contains_v2_heads() -> None:
    manifest = build_label_space_manifest()

    assert set(manifest["multiclass_heads"]) == set(MULTICLASS_HEADS)
    assert set(manifest["multilabel_heads"]) == set(MULTILABEL_HEADS)


def test_export_v2_rows_builds_train_dev_heldout_bundle(tmp_path: Path) -> None:
    input_jsonl = tmp_path / "v2.jsonl"
    _write_jsonl(
        input_jsonl,
        [
            _v2_export_row(row_id="train_001", split="train", modifiers={"follow_up": True}),
            _v2_export_row(
                row_id="dev_001",
                split="dev",
                task_complexity="complex",
                task_shape="compare",
                task_topology="staged",
                context_signals={"clarify_hint": True},
            ),
            _v2_export_row(row_id="held_001", split="heldout", main_intent="unsupported", modifiers={"out_of_scope": True}, safety_bucket=["unsupported"]),
        ],
    )

    bundle = export_v2_rows(input_jsonl_paths=[input_jsonl], include_history=True)
    assert bundle["rows_by_split"]["train"][0]["targets"]["modifiers_active"] == ["follow_up"]
    assert bundle["rows_by_split"]["dev"][0]["targets"]["task_topology"] == "staged"
    assert bundle["rows_by_split"]["heldout"][0]["targets"]["safety_active"] == ["unsupported", "out_of_scope"]


def test_export_v2_rows_raises_on_duplicate_id_by_default(tmp_path: Path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    _write_jsonl(first, [_v2_export_row(row_id="dup_001", split="train")])
    _write_jsonl(second, [_v2_export_row(row_id="dup_001", split="dev")])

    with pytest.raises(ValueError):
        export_v2_rows(input_jsonl_paths=[first, second])


def test_load_and_summarize_v2_bundle_roundtrip(tmp_path: Path) -> None:
    input_jsonl = tmp_path / "v2.jsonl"
    _write_jsonl(
        input_jsonl,
        [
            _v2_export_row(row_id="train_001", split="train", modifiers={"follow_up": True}),
            _v2_export_row(row_id="dev_001", split="dev", context_signals={"clarify_hint": True}),
            _v2_export_row(row_id="held_001", split="heldout", modifiers={"out_of_scope": True}, safety_bucket=["unsupported"]),
        ],
    )
    bundle = export_v2_rows(input_jsonl_paths=[input_jsonl])
    bundle_dir = tmp_path / "bundle"
    write_v2_bundle(bundle_dir, bundle)

    loaded = load_v2_bundle(bundle_dir)
    summary = summarize_v2_bundle(loaded)

    assert summary["train"]["modifier_counts"]["follow_up"] == 1
    assert summary["dev"]["context_counts"]["clarify_hint"] == 1
    assert summary["heldout"]["safety_counts"]["unsupported"] == 1


def test_v2_eval_computes_multiclass_and_multilabel_metrics() -> None:
    multiclass = compute_multiclass_metrics(
        gold=[0, 1, 1, 2],
        pred=[0, 1, 0, 2],
        label_names=["qa", "chat", "system"],
    )
    thresholds = choose_multilabel_thresholds(
        probabilities=[[0.9, 0.2], [0.7, 0.8], [0.2, 0.6]],
        gold=[[1, 0], [1, 1], [0, 1]],
        label_names=["follow_up", "clarify_hint"],
    )
    pred = apply_multilabel_thresholds([[0.9, 0.2], [0.7, 0.8], [0.2, 0.6]], [thresholds["follow_up"], thresholds["clarify_hint"]])
    multilabel = compute_multilabel_metrics(
        gold=[[1, 0], [1, 1], [0, 1]],
        pred=pred,
        label_names=["follow_up", "clarify_hint"],
    )

    assert multiclass["accuracy"] == 0.75
    assert thresholds["follow_up"] >= 0.1
    assert multilabel["micro"]["f1"] == 1.0


def test_v2_train_main_dry_run_writes_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_jsonl = tmp_path / "v2.jsonl"
    _write_jsonl(
        input_jsonl,
        [
            _v2_export_row(row_id="train_001", split="train"),
            _v2_export_row(row_id="dev_001", split="dev"),
            _v2_export_row(row_id="held_001", split="heldout"),
        ],
    )
    bundle = export_v2_rows(input_jsonl_paths=[input_jsonl])
    bundle_dir = tmp_path / "bundle"
    write_v2_bundle(bundle_dir, bundle)
    output_dir = tmp_path / "run"
    monkeypatch.setattr(
        "sys.argv",
        [
            "v2_train_multitask.py",
            str(bundle_dir),
            str(output_dir),
            "--dry-run",
        ],
    )

    exit_code = train_main()

    assert exit_code == 0
    assert (output_dir / "config.json").exists()
    assert (output_dir / "dataset_summary.json").exists()
    assert (output_dir / "README.md").exists()
    assert not (output_dir / "metrics.json").exists()
