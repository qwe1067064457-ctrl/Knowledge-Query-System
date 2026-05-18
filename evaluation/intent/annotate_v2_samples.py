from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from intent import classify_intent  # noqa: E402
from intent.task_compat import infer_topology_from_legacy_task  # noqa: E402
from evaluation.intent.evaluate_intent_rules import load_dataset  # noqa: E402
from evaluation.intent.export_intent_training_set import (  # noqa: E402
    DEFAULT_DEV_DATASET_DIRS,
    DEFAULT_HELDOUT_DATASET_DIRS,
    DEFAULT_TRAIN_DATASET_DIRS,
    _list_default_silver_dataset_dirs,
)
from evaluation.intent.v2_migration import review_reasons_for_v2, should_review_for_v2  # noqa: E402


ClassifierFn = Callable[[str, list[dict[str, Any]]], Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-annotate all intent datasets with current V2 evidence/resolved semantics."
    )
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--dataset-dir", action="append", dest="dataset_dirs", type=Path, default=None)
    return parser.parse_args()


def list_default_dataset_dirs() -> list[Path]:
    return [
        *DEFAULT_TRAIN_DATASET_DIRS,
        *_list_default_silver_dataset_dirs(),
        *DEFAULT_DEV_DATASET_DIRS,
        *DEFAULT_HELDOUT_DATASET_DIRS,
    ]


def annotate_dataset_rows(
    rows: list[dict[str, Any]],
    *,
    dataset_name: str,
    classifier_fn: ClassifierFn = classify_intent,
) -> list[dict[str, Any]]:
    return [
        annotate_row(
            row,
            dataset_name=dataset_name,
            classifier_fn=classifier_fn,
        )
        for row in rows
    ]


def annotate_row(
    row: dict[str, Any],
    *,
    dataset_name: str,
    classifier_fn: ClassifierFn = classify_intent,
) -> dict[str, Any]:
    history = list(row.get("input", {}).get("history") or [])
    query = str(row.get("input", {}).get("user_query", ""))
    analysis = classifier_fn(query, history)

    legacy_gold = dict(row.get("gold", {}))
    comparison = build_label_comparison(legacy_gold=legacy_gold, analysis=analysis)
    legacy_review_reasons = review_reasons_for_v2(row) if should_review_for_v2(row) else []
    comparison_review_reasons = [
        f"changed_{field.replace('.', '_')}"
        for field in comparison["changed_fields"]
    ]
    review_reasons = _unique(legacy_review_reasons + comparison_review_reasons)

    annotated = dict(row)
    annotated["legacy_gold"] = legacy_gold
    annotated["gold"] = {
        "evidence": analysis.evidence.to_v2_dict(),
        "resolved": analysis.resolved.to_dict(),
        "control": analysis.control.to_dict(),
    }
    annotated["label_source"] = "v2_auto_annotator"
    annotated["review_status"] = "draft"
    annotated["annotation_metadata"] = {
        "schema_version": "v2_auto",
        "source_dataset": dataset_name,
    }
    annotated["migration_review"] = {
        "required": bool(review_reasons),
        "reasons": review_reasons,
    }
    annotated["comparison"] = comparison
    return annotated


def build_label_comparison(*, legacy_gold: dict[str, Any], analysis: Any) -> dict[str, Any]:
    legacy_resolved = dict(legacy_gold.get("resolved", {}))
    legacy_task = dict(legacy_resolved.get("task", {}))
    legacy_modifiers = dict(legacy_resolved.get("modifiers", {}))
    legacy_control = dict(legacy_gold.get("control", {}))

    legacy_topology = infer_topology_from_legacy_task(legacy_task)
    changed_fields: list[str] = []

    def compare(path: str, legacy_value: Any, current_value: Any) -> None:
        if legacy_value != current_value:
            changed_fields.append(path)

    compare("resolved.main_intent", legacy_resolved.get("main_intent"), analysis.resolved.main_intent)
    compare("resolved.task.complexity", legacy_task.get("complexity"), analysis.resolved.task.complexity)
    compare("resolved.task.shape", legacy_task.get("shape"), analysis.resolved.task.shape)
    compare("resolved.task.topology", legacy_topology, analysis.resolved.task.topology)
    compare(
        "resolved.context_dependency",
        legacy_resolved.get("context_dependency"),
        analysis.resolved.context_dependency,
    )
    compare("control.route", legacy_control.get("route"), analysis.control.route)
    compare("control.mode", legacy_control.get("mode"), analysis.control.mode)

    for key, value in analysis.resolved.modifiers.to_dict().items():
        compare(f"resolved.modifiers.{key}", legacy_modifiers.get(key), value)

    return {
        "has_changes": bool(changed_fields),
        "changed_fields": changed_fields,
        "legacy_task_topology": legacy_topology,
        "current_task_topology": analysis.resolved.task.topology,
    }


def summarize_annotated_rows(annotated_rows: list[dict[str, Any]]) -> dict[str, Any]:
    changed_counter: Counter[str] = Counter()
    review_reason_counter: Counter[str] = Counter()
    changed_rows = 0
    review_required = 0

    for row in annotated_rows:
        comparison = row.get("comparison", {})
        if comparison.get("has_changes"):
            changed_rows += 1
        changed_counter.update(comparison.get("changed_fields", []))
        migration_review = row.get("migration_review", {})
        if migration_review.get("required"):
            review_required += 1
        review_reason_counter.update(migration_review.get("reasons", []))

    return {
        "total": len(annotated_rows),
        "changed_rows": changed_rows,
        "review_required": review_required,
        "changed_field_counts": dict(sorted(changed_counter.items())),
        "review_reason_counts": dict(sorted(review_reason_counter.items())),
    }


def write_annotated_dataset(output_path: Path, rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def write_summary(output_path: Path, summary_rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_annotation(
    *,
    dataset_dirs: list[Path],
    output_dir: Path,
    classifier_fn: ClassifierFn = classify_intent,
) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []
    for dataset_dir in dataset_dirs:
        rows = load_dataset(dataset_dir)
        annotated_rows = annotate_dataset_rows(
            rows,
            dataset_name=dataset_dir.name,
            classifier_fn=classifier_fn,
        )
        write_annotated_dataset(output_dir / f"{dataset_dir.name}.jsonl", annotated_rows)
        dataset_summary = summarize_annotated_rows(annotated_rows)
        dataset_summary["dataset_dir"] = str(dataset_dir)
        summary_rows.append(dataset_summary)
    write_summary(output_dir / "summary.json", summary_rows)
    return summary_rows


def _unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def main() -> int:
    args = parse_args()
    dataset_dirs = list(args.dataset_dirs or list_default_dataset_dirs())
    summary_rows = run_annotation(dataset_dirs=dataset_dirs, output_dir=args.output_dir)
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "datasets": len(summary_rows),
                "rows": sum(int(item["total"]) for item in summary_rows),
                "review_required": sum(int(item["review_required"]) for item in summary_rows),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
