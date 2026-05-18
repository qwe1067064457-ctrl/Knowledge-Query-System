from __future__ import annotations

from pathlib import Path

from evaluation.intent.evaluate_intent_rules import evaluate_dataset, load_dataset


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "backend_test" / "intent" / "test_data" / "experiments" / "user_batch_v1"


def test_user_batch_v1_dataset_has_expected_batches() -> None:
    rows = load_dataset(DATASET_DIR)

    assert len(rows) == 70
    assert {row["batch"] for row in rows} == {
        "standard_qa",
        "fuzzy_qa",
        "chat",
        "meta",
        "follow_up",
        "mixed_intent",
        "adversarial",
        "long_case_complex",
    }


def test_user_batch_v1_dataset_is_challenging_for_current_rules() -> None:
    rows = load_dataset(DATASET_DIR)
    summary = evaluate_dataset(rows)

    assert summary["overall"]["samples"] == 70
    assert 0.9 <= summary["overall"]["resolved_main_intent_accuracy"] < 0.97
    assert summary["overall"]["resolved_shape_accuracy"] < 0.8
    assert summary["per_batch"]["long_case_complex"]["control_route_accuracy"] < 0.5
