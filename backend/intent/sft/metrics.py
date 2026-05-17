from __future__ import annotations

from typing import Any


def apply_thresholds(probabilities: list[list[float]], thresholds: list[float]) -> list[list[int]]:
    return [
        [1 if score >= threshold else 0 for score, threshold in zip(row, thresholds)]
        for row in probabilities
    ]


def choose_thresholds(
    *,
    probabilities: list[list[float]],
    gold: list[list[int]],
    label_names: list[str],
    candidate_thresholds: list[float] | None = None,
) -> dict[str, float]:
    if len(probabilities) != len(gold):
        raise ValueError("probabilities and gold must have the same number of rows")

    thresholds = candidate_thresholds or [round(value, 2) for value in _frange(0.1, 0.9, 0.05)]
    chosen: dict[str, float] = {}
    for label_index, label_name in enumerate(label_names):
        positives = sum(row[label_index] for row in gold)
        if positives == 0:
            chosen[label_name] = 0.5
            continue

        best_threshold = 0.5
        best_f1 = -1.0
        best_distance = float("inf")
        for threshold in thresholds:
            pred = [1 if row[label_index] >= threshold else 0 for row in probabilities]
            metrics = _binary_metrics([row[label_index] for row in gold], pred)
            f1 = metrics["f1"]
            distance = abs(threshold - 0.5)
            if f1 > best_f1 or (f1 == best_f1 and distance < best_distance):
                best_f1 = f1
                best_threshold = threshold
                best_distance = distance
        chosen[label_name] = best_threshold
    return chosen


def compute_multilabel_metrics(
    *,
    gold: list[list[int]],
    pred: list[list[int]],
    label_names: list[str],
) -> dict[str, Any]:
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have the same number of rows")
    if any(len(row) != len(label_names) for row in gold + pred):
        raise ValueError("row width must match label_names length")

    per_signal: dict[str, Any] = {}
    macro_values: list[float] = []
    micro_tp = micro_fp = micro_fn = 0

    for label_index, label_name in enumerate(label_names):
        gold_col = [row[label_index] for row in gold]
        pred_col = [row[label_index] for row in pred]
        metrics = _binary_metrics(gold_col, pred_col)
        per_signal[label_name] = metrics
        macro_values.append(metrics["f1"])
        micro_tp += metrics["tp"]
        micro_fp += metrics["fp"]
        micro_fn += metrics["fn"]

    micro_precision = _safe_divide(micro_tp, micro_tp + micro_fp)
    micro_recall = _safe_divide(micro_tp, micro_tp + micro_fn)
    micro_f1 = _safe_divide(2 * micro_precision * micro_recall, micro_precision + micro_recall)
    exact_match = _safe_divide(sum(1 for g, p in zip(gold, pred) if g == p), len(gold))

    return {
        "rows": len(gold),
        "per_signal": per_signal,
        "micro": {
            "precision": _round_metric(micro_precision),
            "recall": _round_metric(micro_recall),
            "f1": _round_metric(micro_f1),
            "tp": micro_tp,
            "fp": micro_fp,
            "fn": micro_fn,
        },
        "macro": {
            "f1": _round_metric(sum(macro_values) / len(macro_values) if macro_values else 0.0),
        },
        "exact_match_accuracy": _round_metric(exact_match),
    }


def _binary_metrics(gold: list[int], pred: list[int]) -> dict[str, Any]:
    tp = sum(1 for g, p in zip(gold, pred) if g == 1 and p == 1)
    fp = sum(1 for g, p in zip(gold, pred) if g == 0 and p == 1)
    fn = sum(1 for g, p in zip(gold, pred) if g == 1 and p == 0)
    tn = sum(1 for g, p in zip(gold, pred) if g == 0 and p == 0)
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    return {
        "precision": _round_metric(precision),
        "recall": _round_metric(recall),
        "f1": _round_metric(f1),
        "support": {
            "positive": sum(gold),
            "negative": len(gold) - sum(gold),
        },
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _round_metric(value: float) -> float:
    return round(value, 6)


def _frange(start: float, stop: float, step: float) -> list[float]:
    values: list[float] = []
    current = start
    while current <= stop + 1e-9:
        values.append(round(current, 2))
        current += step
    return values
