from __future__ import annotations

from collections import Counter
from typing import Any


def apply_multilabel_thresholds(probabilities: list[list[float]], thresholds: list[float]) -> list[list[int]]:
    return [
        [1 if score >= threshold else 0 for score, threshold in zip(row, thresholds)]
        for row in probabilities
    ]


def choose_multilabel_thresholds(
    *,
    probabilities: list[list[float]],
    gold: list[list[int]],
    label_names: list[str],
    candidate_thresholds: list[float] | None = None,
) -> dict[str, float]:
    candidate_values = candidate_thresholds or [round(value, 2) for value in _frange(0.1, 0.9, 0.05)]
    thresholds: dict[str, float] = {}
    for index, label in enumerate(label_names):
        label_gold = [row[index] for row in gold]
        label_probs = [row[index] for row in probabilities]
        if sum(label_gold) == 0:
            thresholds[label] = 0.5
            continue

        best_threshold = 0.5
        best_f1 = -1.0
        for threshold in candidate_values:
            pred = [1 if score >= threshold else 0 for score in label_probs]
            metrics = _binary_metrics(gold=label_gold, pred=pred)
            if metrics["f1"] > best_f1:
                best_f1 = metrics["f1"]
                best_threshold = threshold
        thresholds[label] = best_threshold
    return thresholds


def compute_multiclass_metrics(
    *,
    gold: list[int],
    pred: list[int],
    label_names: list[str],
) -> dict[str, Any]:
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have the same length")

    rows = len(gold)
    correct = sum(1 for gold_label, pred_label in zip(gold, pred) if gold_label == pred_label)
    confusion = [[0 for _ in label_names] for _ in label_names]
    for gold_label, pred_label in zip(gold, pred):
        confusion[gold_label][pred_label] += 1

    per_label: dict[str, Any] = {}
    f1_values: list[float] = []
    for label_index, label in enumerate(label_names):
        tp = confusion[label_index][label_index]
        fp = sum(confusion[row][label_index] for row in range(len(label_names)) if row != label_index)
        fn = sum(confusion[label_index][col] for col in range(len(label_names)) if col != label_index)
        tn = rows - tp - fp - fn
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        support = sum(1 for value in gold if value == label_index)
        f1_values.append(f1)
        per_label[label] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }

    return {
        "rows": rows,
        "accuracy": round(correct / rows, 6) if rows else 0.0,
        "macro_f1": round(sum(f1_values) / len(f1_values), 6) if f1_values else 0.0,
        "per_label": per_label,
        "confusion_matrix": {
            "labels": label_names,
            "matrix": confusion,
        },
    }


def compute_multilabel_metrics(
    *,
    gold: list[list[int]],
    pred: list[list[int]],
    label_names: list[str],
) -> dict[str, Any]:
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have the same length")

    per_signal: dict[str, Any] = {}
    macro_f1_values: list[float] = []
    tp_total = fp_total = fn_total = 0
    rows = len(gold)
    exact_match = 0

    for gold_row, pred_row in zip(gold, pred):
        if gold_row == pred_row:
            exact_match += 1

    for index, label in enumerate(label_names):
        label_gold = [row[index] for row in gold]
        label_pred = [row[index] for row in pred]
        metrics = _binary_metrics(gold=label_gold, pred=label_pred)
        positive = sum(label_gold)
        negative = len(label_gold) - positive
        per_signal[label] = {
            "precision": round(metrics["precision"], 6),
            "recall": round(metrics["recall"], 6),
            "f1": round(metrics["f1"], 6),
            "support": {
                "positive": positive,
                "negative": negative,
            },
            "tp": metrics["tp"],
            "fp": metrics["fp"],
            "fn": metrics["fn"],
            "tn": metrics["tn"],
        }
        macro_f1_values.append(metrics["f1"])
        tp_total += metrics["tp"]
        fp_total += metrics["fp"]
        fn_total += metrics["fn"]

    micro_precision = tp_total / (tp_total + fp_total) if (tp_total + fp_total) else 0.0
    micro_recall = tp_total / (tp_total + fn_total) if (tp_total + fn_total) else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall)
        else 0.0
    )

    return {
        "rows": rows,
        "per_signal": per_signal,
        "micro": {
            "precision": round(micro_precision, 6),
            "recall": round(micro_recall, 6),
            "f1": round(micro_f1, 6),
            "tp": tp_total,
            "fp": fp_total,
            "fn": fn_total,
        },
        "macro": {
            "f1": round(sum(macro_f1_values) / len(macro_f1_values), 6) if macro_f1_values else 0.0,
        },
        "exact_match_accuracy": round(exact_match / rows, 6) if rows else 0.0,
    }


def _binary_metrics(*, gold: list[int], pred: list[int]) -> dict[str, Any]:
    tp = sum(1 for gold_value, pred_value in zip(gold, pred) if gold_value == 1 and pred_value == 1)
    fp = sum(1 for gold_value, pred_value in zip(gold, pred) if gold_value == 0 and pred_value == 1)
    fn = sum(1 for gold_value, pred_value in zip(gold, pred) if gold_value == 1 and pred_value == 0)
    tn = sum(1 for gold_value, pred_value in zip(gold, pred) if gold_value == 0 and pred_value == 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _frange(start: float, stop: float, step: float) -> list[float]:
    values: list[float] = []
    current = start
    while current <= stop + 1e-8:
        values.append(round(current, 2))
        current += step
    return values
