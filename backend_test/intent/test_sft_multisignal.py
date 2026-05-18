from __future__ import annotations

import json
from pathlib import Path

import pytest

from intent.sft.data import (
    DEFAULT_BOUNDARY_SIGNAL_LABELS,
    DEFAULT_DEV_DATASET_DIRS,
    DEFAULT_HELDOUT_DATASET_DIRS,
    build_query_text,
    export_signal_rows,
    extract_required_signal_vector,
    load_multilabel_bundle,
    summarize_bundle,
    write_multilabel_bundle,
)
from intent.sft.metrics import apply_thresholds, choose_thresholds, compute_multilabel_metrics
from intent.sft.train import main as train_main


def _dataset_row(
    *,
    row_id: str,
    user_query: str,
    required_signals: list[str],
    history: list[dict[str, str]] | None = None,
) -> dict:
    return {
        "id": row_id,
        "batch": "test_batch",
        "input": {
            "user_query": user_query,
            "history": history or [],
        },
        "gold": {
            "evidence": {
                "classifier_mode": "rule_plus_model",
                "required_signals": required_signals,
                "required_rule_ids": [],
                "rule_expectations": {},
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
                    "soft_doubt": "soft_doubt" in required_signals,
                },
                "task": {
                    "complexity": "simple",
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
        "label_tier": "gold",
    }


def _write_dataset(dataset_dir: Path, filename: str, rows: list[dict]) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    (dataset_dir / filename).write_text(json.dumps(rows, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_bundle(bundle_dir: Path) -> None:
    write_multilabel_bundle(
        bundle_dir,
        {
            "task_name": "required_signals_multilabel",
            "label_names": ["soft_doubt", "follow_up", "needs_clarification"],
            "include_history": False,
            "label_group": "boundary_signals_v1",
            "rows_by_split": {
                "train": [
                    {
                        "id": "train_001",
                        "text": "你刚才那个结论是不是太绝对了",
                        "labels": [1, 0, 0],
                        "active_labels": ["soft_doubt"],
                        "source_dataset": "fixture",
                        "label_tier": "gold",
                        "split": "train",
                    }
                ],
                "dev": [
                    {
                        "id": "dev_001",
                        "text": "这个我没太听懂，能再解释一下吗",
                        "labels": [0, 0, 1],
                        "active_labels": ["needs_clarification"],
                        "source_dataset": "fixture",
                        "label_tier": "gold",
                        "split": "dev",
                    }
                ],
                "calibration": [
                    {
                        "id": "cal_001",
                        "text": "再展开一下",
                        "labels": [0, 1, 0],
                        "active_labels": ["follow_up"],
                        "source_dataset": "fixture",
                        "label_tier": "gold",
                        "split": "calibration",
                    }
                ],
                "heldout": [
                    {
                        "id": "heldout_001",
                        "text": "你刚才那个依据是什么",
                        "labels": [1, 1, 0],
                        "active_labels": ["soft_doubt", "follow_up"],
                        "source_dataset": "fixture",
                        "label_tier": "gold",
                        "split": "heldout",
                    }
                ],
            },
        },
    )


def test_build_query_text_defaults_to_query_only_and_can_include_history() -> None:
    input_block = {
        "user_query": "现在的问题",
        "history": [{"role": "assistant", "content": "前文"}],
    }

    assert build_query_text(input_block) == "现在的问题"
    with_history = build_query_text(input_block, include_history=True)
    assert "[历史]" in with_history
    assert "[当前问题]" in with_history


def test_extract_required_signal_vector_marks_known_labels_and_ignores_others() -> None:
    labels, active_labels = extract_required_signal_vector(
        {"required_signals": ["soft_doubt", "follow_up", "non_existing"]},
        label_names=["soft_doubt", "follow_up", "needs_clarification"],
    )

    assert labels == [1, 1, 0]
    assert active_labels == ["soft_doubt", "follow_up"]


def test_export_signal_rows_builds_train_dev_calibration_and_heldout_splits(tmp_path: Path) -> None:
    train_dir = tmp_path / "train"
    dev_dir = tmp_path / "dev"
    calibration_dir = tmp_path / "calibration"
    heldout_dir = tmp_path / "heldout"
    _write_dataset(train_dir, "rows.json", [_dataset_row(row_id="train_001", user_query="A", required_signals=["soft_doubt"])])
    _write_dataset(dev_dir, "rows.json", [_dataset_row(row_id="dev_001", user_query="B", required_signals=["needs_clarification"])])
    _write_dataset(calibration_dir, "rows.json", [_dataset_row(row_id="cal_001", user_query="C", required_signals=["follow_up"])])
    _write_dataset(heldout_dir, "rows.json", [_dataset_row(row_id="held_001", user_query="D", required_signals=["soft_doubt", "follow_up"])])

    bundle = export_signal_rows(
        train_dataset_dirs=[train_dir],
        silver_dataset_dirs=[],
        dev_dataset_dirs=[dev_dir],
        calibration_dataset_dirs=[calibration_dir],
        heldout_dataset_dirs=[heldout_dir],
        signal_labels=["soft_doubt", "follow_up", "needs_clarification"],
    )

    assert bundle["label_group"] == "boundary_signals_v1"
    assert bundle["rows_by_split"]["train"][0]["labels"] == [1, 0, 0]
    assert bundle["rows_by_split"]["dev"][0]["labels"] == [0, 0, 1]
    assert bundle["rows_by_split"]["calibration"][0]["labels"] == [0, 1, 0]
    assert bundle["rows_by_split"]["heldout"][0]["labels"] == [1, 1, 0]


def test_load_multilabel_bundle_reads_all_required_splits_and_raises_on_missing_split(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle(bundle_dir)

    bundle = load_multilabel_bundle(bundle_dir)
    assert bundle["label_names"] == ["soft_doubt", "follow_up", "needs_clarification"]
    assert bundle["label_group"] == "boundary_signals_v1"
    assert [example.id for example in bundle["splits"]["heldout"]] == ["heldout_001"]

    broken_dir = tmp_path / "broken_bundle"
    broken_dir.mkdir()
    (broken_dir / "label_map.json").write_text(json.dumps({"qa": 0}, ensure_ascii=False), encoding="utf-8")
    (broken_dir / "train.jsonl").write_text("", encoding="utf-8")
    (broken_dir / "dev.jsonl").write_text("", encoding="utf-8")
    (broken_dir / "calibration.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        load_multilabel_bundle(broken_dir)


def test_summarize_bundle_reports_signal_counts(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle(bundle_dir)
    bundle = load_multilabel_bundle(bundle_dir)

    summary = summarize_bundle(bundle)

    assert summary["train"]["active_signal_counts"]["soft_doubt"] == 1
    assert summary["heldout"]["active_signal_counts"]["follow_up"] == 1
    assert list(DEFAULT_BOUNDARY_SIGNAL_LABELS) == [
        "soft_doubt",
        "follow_up",
        "needs_clarification",
        "ask_source",
        "multi_question",
        "complex",
    ]


def test_default_split_dirs_point_to_backfilled_dev_and_heldout_v3() -> None:
    assert DEFAULT_DEV_DATASET_DIRS[0].name == "seed_query_20260517_gold_v2"
    assert DEFAULT_HELDOUT_DATASET_DIRS[0].name == "frozen_heldout_v3"


def test_compute_multilabel_metrics_and_threshold_selection_behave_as_expected() -> None:
    gold = [[1, 0], [1, 1], [0, 1]]
    probabilities = [[0.8, 0.2], [0.7, 0.6], [0.4, 0.9]]
    pred = apply_thresholds(probabilities, [0.5, 0.5])

    metrics = compute_multilabel_metrics(gold=gold, pred=pred, label_names=["soft_doubt", "follow_up"])
    thresholds = choose_thresholds(probabilities=probabilities, gold=gold, label_names=["soft_doubt", "follow_up"])
    fallback_thresholds = choose_thresholds(
        probabilities=[[0.2, 0.3], [0.1, 0.4]],
        gold=[[0, 0], [0, 0]],
        label_names=["soft_doubt", "follow_up"],
    )

    assert metrics["micro"]["f1"] == 1.0
    assert metrics["macro"]["f1"] == 1.0
    assert set(thresholds) == {"soft_doubt", "follow_up"}
    assert all(0.1 <= value <= 0.9 for value in thresholds.values())
    assert fallback_thresholds == {"soft_doubt": 0.5, "follow_up": 0.5}


def test_train_main_dry_run_writes_reports_without_training_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle_dir = tmp_path / "bundle"
    output_dir = tmp_path / "run_output"
    _write_bundle(bundle_dir)
    monkeypatch.setattr(
        "sys.argv",
        [
            "train.py",
            str(bundle_dir),
            str(output_dir),
            "--dry-run",
        ],
    )

    exit_code = train_main()

    assert exit_code == 0
    summary = json.loads((output_dir / "dataset_summary.json").read_text(encoding="utf-8"))
    assert summary["calibration"]["rows"] == 1
    config = json.loads((output_dir / "config.json").read_text(encoding="utf-8"))
    assert config["gold_weight"] == 1.0
    assert config["silver_weight"] == 0.4
    assert not (output_dir / "metrics.json").exists()
    assert not (output_dir / "thresholds.json").exists()
