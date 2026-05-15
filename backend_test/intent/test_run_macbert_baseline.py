from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.intent.run_macbert_baseline import (
    build_error_rows,
    compute_metrics,
    load_task_bundle,
    main,
    summarize_bundle,
    write_report_bundle,
)


def _write_task_bundle(task_dir: Path) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "label_map.json").write_text(json.dumps({"false": 0, "true": 1}, ensure_ascii=False), encoding="utf-8")
    (task_dir / "train.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "train_001",
                        "text": "[当前问题]\n这个说法是不是太绝对了？",
                        "label": 1,
                        "label_name": "true",
                        "source_dataset": "fixture_train",
                        "label_tier": "gold",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "id": "train_002",
                        "text": "[当前问题]\n请直接解释规则。",
                        "label": 0,
                        "label_name": "false",
                        "source_dataset": "fixture_train",
                        "label_tier": "gold",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (task_dir / "dev.jsonl").write_text(
        json.dumps(
            {
                "id": "dev_001",
                "text": "[当前问题]\n你确定没有例外吗？",
                "label": 1,
                "label_name": "true",
                "source_dataset": "fixture_dev",
                "label_tier": "gold",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (task_dir / "heldout.jsonl").write_text(
        json.dumps(
            {
                "id": "heldout_001",
                "text": "[当前问题]\n请总结这个方案。",
                "label": 0,
                "label_name": "false",
                "source_dataset": "fixture_heldout",
                "label_tier": "gold",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def test_load_task_bundle_reads_all_required_splits(tmp_path: Path) -> None:
    task_dir = tmp_path / "soft_doubt"
    _write_task_bundle(task_dir)

    bundle = load_task_bundle(task_dir)
    summary = summarize_bundle(bundle)

    assert bundle["task_name"] == "soft_doubt"
    assert [example.id for example in bundle["splits"]["train"]] == ["train_001", "train_002"]
    assert summary["splits"]["dev"]["labels"] == {"true": 1}


def test_load_task_bundle_raises_when_split_is_missing(tmp_path: Path) -> None:
    task_dir = tmp_path / "soft_doubt"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "label_map.json").write_text(json.dumps({"false": 0, "true": 1}, ensure_ascii=False), encoding="utf-8")
    (task_dir / "train.jsonl").write_text("", encoding="utf-8")
    (task_dir / "dev.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        load_task_bundle(task_dir)


def test_compute_metrics_for_soft_doubt_returns_binary_scores() -> None:
    metrics = compute_metrics(
        task_name="soft_doubt",
        label_names=["false", "true"],
        gold=[1, 0, 1, 0],
        pred=[1, 1, 0, 0],
    )

    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["confusion"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}


def test_compute_metrics_for_task_shape_returns_macro_f1_and_confusion() -> None:
    metrics = compute_metrics(
        task_name="task_shape",
        label_names=["single_question", "verify", "compare"],
        gold=[0, 1, 2],
        pred=[0, 2, 2],
    )

    assert metrics["accuracy"] == round(2 / 3, 6)
    assert metrics["macro_f1"] == round((1.0 + 0.0 + round(2 / 3, 6)) / 3, 6)
    assert metrics["confusion_matrix"]["matrix"] == [
        [1, 0, 0],
        [0, 0, 1],
        [0, 0, 1],
    ]


def test_build_error_rows_only_keeps_mismatches(tmp_path: Path) -> None:
    task_dir = tmp_path / "soft_doubt"
    _write_task_bundle(task_dir)
    bundle = load_task_bundle(task_dir)

    errors = build_error_rows(bundle["splits"]["heldout"], [1], ["false", "true"])

    assert errors == [
        {
            "id": "heldout_001",
            "text": "[当前问题]\n请总结这个方案。",
            "gold_label": "false",
            "pred_label": "true",
            "source_dataset": "fixture_heldout",
            "label_tier": "gold",
        }
    ]


def test_write_report_bundle_writes_summary_and_metrics_files(tmp_path: Path) -> None:
    dataset_summary = {
        "task_name": "soft_doubt",
        "task_dir": str(tmp_path / "soft_doubt"),
        "label_map": {"false": 0, "true": 1},
        "splits": {
            "train": {"rows": 2, "labels": {"false": 1, "true": 1}},
            "dev": {"rows": 1, "labels": {"true": 1}},
            "heldout": {"rows": 1, "labels": {"false": 1}},
        },
    }
    metrics = {
        "train": {"accuracy": 1.0},
        "dev": {"accuracy": 0.0},
        "heldout": {"accuracy": 0.0},
    }
    errors = [{"id": "heldout_001", "gold_label": "false", "pred_label": "true"}]

    write_report_bundle(
        tmp_path / "run_output",
        config={"task_name": "soft_doubt", "dry_run": False},
        dataset_summary=dataset_summary,
        metrics_by_split=metrics,
        errors=errors,
    )

    assert json.loads((tmp_path / "run_output" / "metrics.json").read_text(encoding="utf-8"))["heldout"]["accuracy"] == 0.0
    assert (tmp_path / "run_output" / "heldout_errors.jsonl").read_text(encoding="utf-8").strip()
    assert "Heldout Errors" in (tmp_path / "run_output" / "README.md").read_text(encoding="utf-8")


def test_main_dry_run_emits_dataset_reports_without_training_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    task_dir = tmp_path / "soft_doubt"
    output_dir = tmp_path / "macbert_run"
    _write_task_bundle(task_dir)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_macbert_baseline.py",
            str(task_dir),
            str(output_dir),
            "--dry-run",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    assert json.loads((output_dir / "dataset_summary.json").read_text(encoding="utf-8"))["splits"]["train"]["rows"] == 2
    assert not (output_dir / "metrics.json").exists()
