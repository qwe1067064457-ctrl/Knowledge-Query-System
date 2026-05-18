from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from intent import classify_intent  # noqa: E402
from intent.task_compat import infer_topology_from_legacy_task  # noqa: E402
from evaluation.intent.v2_migration import infer_context_signals_from_dependency  # noqa: E402


OVERALL_KEYS = (
    "evidence_mode",
    "evidence_required_signals",
    "evidence_required_rules",
    "evidence_dependency",
    "evidence_unsupported",
    "resolved_main_intent",
    "resolved_complexity",
    "resolved_shape",
    "resolved_topology",
    "resolved_context",
    "control_route",
    "control_mode",
)


def load_dataset(dataset_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(dataset_dir)
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Dataset file must contain a list: {path}")
        rows.extend(payload)
    return rows


def load_rule_supervision(annotation_path: str | Path) -> list[dict[str, Any]]:
    path = Path(annotation_path)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("review_status") not in {"approved", "approved_with_note"}:
            continue
        rows.append(payload)
    return rows


def build_rule_supervision_rows_from_dataset(
    rows: list[dict[str, Any]],
    *,
    reviewer: str = "gold_dataset",
    review_status: str = "approved",
    notes_prefix: str = "imported from gold dataset",
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        batch = row["batch"]
        input_payload = row["input"]
        evidence = row["gold"]["evidence"]
        source_query_id = row.get("source_query_id", "")
        for rule_id, expected in evidence.get("rule_expectations", {}).items():
            flattened.append(
                {
                    "id": f"{row['id']}__{rule_id}",
                    "batch": batch,
                    "input": {
                        "user_query": input_payload["user_query"],
                        "history": input_payload.get("history") or [],
                    },
                    "target_rule_id": rule_id,
                    "expected": expected,
                    "rationale": row.get("notes", ""),
                    "review_status": review_status,
                    "reviewer": reviewer,
                    "notes": f"{notes_prefix}; source_query_id={source_query_id or row['id']}",
                }
            )
    return flattened


def load_rule_supervision_dataset(dataset_dir: str | Path) -> list[dict[str, Any]]:
    return build_rule_supervision_rows_from_dataset(load_dataset(dataset_dir))


def evaluate_dataset(
    rows: list[dict[str, Any]],
    *,
    rule_supervision_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    overall_counts = _new_metric_counter()
    per_batch_counts: dict[str, dict[str, int]] = defaultdict(_new_metric_counter)
    rule_stats: dict[str, dict[str, int | float]] = defaultdict(_new_rule_stat_counter)

    for row in rows:
        analysis = classify_intent(
            row["input"]["user_query"],
            row["input"].get("history") or [],
        )
        batch = row["batch"]
        gold = row["gold"]

        checks = {
            "evidence_mode": analysis.evidence.classifier_mode == gold["evidence"]["classifier_mode"],
            "evidence_required_signals": _required_subset(
                gold["evidence"].get("required_signals", []),
                analysis.evidence.signal_buckets.all_signals(),
            ),
            "evidence_required_rules": _required_subset(
                gold["evidence"].get("required_rule_ids", []),
                [match.rule_id for match in analysis.evidence.matched_rules],
            ),
            "evidence_dependency": _dict_equal(
                infer_context_signals_from_dependency(gold["evidence"].get("dependency_signals", {})),
                analysis.evidence.context_signals.to_dict(),
            ),
            "evidence_unsupported": _dict_equal(
                gold["evidence"].get("unsupported_signals", {}),
                analysis.evidence.unsupported_signals,
            ),
            "resolved_main_intent": analysis.resolved.main_intent == gold["resolved"]["main_intent"],
            "resolved_complexity": analysis.resolved.task.complexity == gold["resolved"]["task"]["complexity"],
            "resolved_shape": analysis.resolved.task.shape == gold["resolved"]["task"]["shape"],
            "resolved_topology": analysis.resolved.task.topology == _expected_topology(gold["resolved"]["task"]),
            "resolved_context": analysis.resolved.context_dependency == gold["resolved"]["context_dependency"],
            "control_route": analysis.control.route == gold["control"]["route"],
            "control_mode": analysis.control.mode == gold["control"]["mode"],
        }

        _accumulate_metrics(overall_counts, checks)
        _accumulate_metrics(per_batch_counts[batch], checks)
        _accumulate_rule_stats(
            rule_stats,
            expected_rules=gold["evidence"].get("rule_expectations", {}),
            matched_rule_ids={match.rule_id for match in analysis.evidence.matched_rules},
            required_rule_ids=set(gold["evidence"].get("required_rule_ids", [])),
        )

    for supervision in rule_supervision_rows or []:
        analysis = classify_intent(
            supervision["input"]["user_query"],
            supervision["input"].get("history") or [],
        )
        _accumulate_rule_stats(
            rule_stats,
            expected_rules={supervision["target_rule_id"]: supervision["expected"]},
            matched_rule_ids={match.rule_id for match in analysis.evidence.matched_rules},
            required_rule_ids=set(),
        )

    overall = _finalize_metrics(overall_counts)
    per_batch = {batch: _finalize_metrics(counts) for batch, counts in sorted(per_batch_counts.items())}
    finalized_rule_stats = {
        rule_id: _finalize_rule_stats(stats)
        for rule_id, stats in sorted(rule_stats.items())
    }
    return {
        "overall": overall,
        "per_batch": per_batch,
        "rule_stats": finalized_rule_stats,
    }


def _new_metric_counter() -> dict[str, int]:
    counter = {"samples": 0}
    for key in OVERALL_KEYS:
        counter[f"{key}_correct"] = 0
    return counter


def _accumulate_metrics(counter: dict[str, int], checks: dict[str, bool]) -> None:
    counter["samples"] += 1
    for key, passed in checks.items():
        if passed:
            counter[f"{key}_correct"] += 1


def _finalize_metrics(counter: dict[str, int]) -> dict[str, int | float]:
    samples = counter["samples"]
    result: dict[str, int | float] = {"samples": samples}
    for key in OVERALL_KEYS:
        correct = counter[f"{key}_correct"]
        result[f"{key}_correct"] = correct
        result[f"{key}_accuracy"] = round(correct / samples, 4) if samples else 0.0
    return result


def _new_rule_stat_counter() -> dict[str, int | float]:
    return {
        "hits": 0,
        "required_hits": 0,
        "labeled_samples": 0,
        "expected_positive": 0,
        "expected_negative": 0,
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tn": 0,
    }


def _accumulate_rule_stats(
    rule_stats: dict[str, dict[str, int | float]],
    *,
    expected_rules: dict[str, bool],
    matched_rule_ids: set[str],
    required_rule_ids: set[str],
) -> None:
    all_rule_ids = set(expected_rules) | matched_rule_ids | required_rule_ids
    for rule_id in all_rule_ids:
        stats = rule_stats[rule_id]
        actual = rule_id in matched_rule_ids
        if actual:
            stats["hits"] += 1
        if rule_id in required_rule_ids and actual:
            stats["required_hits"] += 1

        if rule_id not in expected_rules:
            continue

        expected = expected_rules[rule_id]
        stats["labeled_samples"] += 1
        if expected:
            stats["expected_positive"] += 1
        else:
            stats["expected_negative"] += 1

        if expected and actual:
            stats["tp"] += 1
        elif expected and not actual:
            stats["fn"] += 1
        elif not expected and actual:
            stats["fp"] += 1
        else:
            stats["tn"] += 1


def _finalize_rule_stats(stats: dict[str, int | float]) -> dict[str, int | float]:
    tp = int(stats["tp"])
    fp = int(stats["fp"])
    fn = int(stats["fn"])
    tn = int(stats["tn"])
    labeled_samples = int(stats["labeled_samples"])
    expected_positive = int(stats["expected_positive"])
    required_positive = expected_positive

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    accuracy = (tp + tn) / labeled_samples if labeled_samples else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    required_hit_rate = int(stats["required_hits"]) / required_positive if required_positive else 0.0

    return {
        "hits": int(stats["hits"]),
        "required_hits": int(stats["required_hits"]),
        "required_hit_rate": round(required_hit_rate, 4),
        "labeled_samples": labeled_samples,
        "expected_positive": expected_positive,
        "expected_negative": int(stats["expected_negative"]),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "accuracy": round(accuracy, 4),
        "f1": round(f1, 4),
    }


def _required_subset(required: list[str], actual: list[str] | tuple[str, ...]) -> bool:
    return set(required).issubset(set(actual))


def _dict_equal(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            return False
    return True


def _expected_topology(task_payload: dict[str, Any]) -> str:
    return infer_topology_from_legacy_task(task_payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate intent dataset rows against the current classifier.")
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--rule-supervision-file", type=Path, default=None)
    args = parser.parse_args()

    summary = evaluate_dataset(
        load_dataset(args.dataset_dir),
        rule_supervision_rows=load_rule_supervision(args.rule_supervision_file) if args.rule_supervision_file else None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
