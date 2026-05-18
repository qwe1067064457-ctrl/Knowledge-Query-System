from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.intent.signal_taxonomy import (
    EXPECTED_BUCKETS,
    find_unknown_signals,
    normalize_signal_buckets,
    split_cross_bucket_conflicts,
)
from intent.task_compat import infer_topology_from_legacy_task

CHECK_FIELDS = (
    "main_intent",
    "modifiers",
    "task",
    "context_dependency",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run automatic quality gates for V2 auto annotations.")
    parser.add_argument("annotation_report_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args()


def run_quality_gate(annotation_report_dir: Path) -> dict[str, Any]:
    rows = load_rows(annotation_report_dir)
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    distribution_counter = {
        "legacy": defaultdict(Counter),
        "current": defaultdict(Counter),
    }

    for row in rows:
        violations.extend(check_row_completeness(row))
        taxonomy_violations, taxonomy_warnings = check_signal_taxonomy(row)
        violations.extend(taxonomy_violations)
        warnings.extend(taxonomy_warnings)
        violations.extend(check_resolved_consistency(row))
        collect_distribution(distribution_counter, row)

    warnings.extend(check_distribution_drift(distribution_counter))

    return {
        "rows": len(rows),
        "violations": violations,
        "warnings": warnings,
        "violation_count": len(violations),
        "warning_count": len(warnings),
    }


def load_rows(annotation_report_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(annotation_report_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def check_row_completeness(row: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    resolved = row.get("gold", {}).get("resolved", {})
    for field in CHECK_FIELDS:
        if field not in resolved:
            violations.append(_issue(row, "missing_field", f"resolved.{field}"))
    task = resolved.get("task", {})
    for field in ("complexity", "shape", "topology"):
        if field not in task:
            violations.append(_issue(row, "missing_field", f"resolved.task.{field}"))
    evidence = row.get("gold", {}).get("evidence", {})
    buckets = evidence.get("signal_buckets", {})
    for bucket in EXPECTED_BUCKETS:
        if bucket not in buckets:
            violations.append(_issue(row, "missing_bucket", bucket))
    return violations


def check_signal_taxonomy(row: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    evidence = row.get("gold", {}).get("evidence", {})
    buckets = normalize_signal_buckets(evidence)
    for bucket, signals in find_unknown_signals(buckets).items():
        violations.append(_issue(row, "unknown_signal", f"{bucket}:{','.join(signals)}"))
    allowed_overlaps, conflict_overlaps = split_cross_bucket_conflicts(buckets)
    for signal, bucket_names in allowed_overlaps.items():
        warnings.append(_issue(row, "allowed_cross_bucket_signal", f"{signal}:{','.join(bucket_names)}"))
    for signal, bucket_names in conflict_overlaps.items():
        violations.append(_issue(row, "cross_bucket_signal", f"{signal}:{','.join(bucket_names)}"))
    return violations, warnings


def check_resolved_consistency(row: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    resolved = row.get("gold", {}).get("resolved", {})
    main_intent = resolved.get("main_intent")
    modifiers = resolved.get("modifiers", {})
    task = resolved.get("task", {})
    complexity = task.get("complexity")
    shape = task.get("shape")
    topology = task.get("topology")

    if complexity == "compound" and topology not in {"parallel_queries", "parallel_subtasks"}:
        violations.append(_issue(row, "inconsistent_task", "compound_requires_parallel_topology"))
    if complexity == "compound" and shape != "multi_question":
        violations.append(_issue(row, "inconsistent_task", "compound_requires_multi_question_shape"))
    if topology == "staged" and complexity != "complex":
        violations.append(_issue(row, "inconsistent_task", "staged_requires_complex"))
    if topology in {"parallel_queries", "parallel_subtasks"} and complexity != "compound":
        violations.append(_issue(row, "inconsistent_task", "parallel_topology_requires_compound"))
    if main_intent in {"chat", "system", "unsupported"} and shape != "none":
        violations.append(_issue(row, "inconsistent_task", f"{main_intent}_requires_none_shape"))
    if modifiers.get("ask_capability") and main_intent != "system":
        violations.append(_issue(row, "inconsistent_modifier", "ask_capability_requires_system"))
    if modifiers.get("out_of_scope") and main_intent != "unsupported":
        violations.append(_issue(row, "inconsistent_modifier", "out_of_scope_requires_unsupported"))
    if modifiers.get("ask_source") and main_intent != "qa":
        violations.append(_issue(row, "inconsistent_modifier", "ask_source_requires_qa"))
    return violations


def collect_distribution(distribution_counter: dict[str, Any], row: dict[str, Any]) -> None:
    legacy = row.get("legacy_gold", {}).get("resolved", {})
    current = row.get("gold", {}).get("resolved", {})
    legacy_task = legacy.get("task", {})
    current_task = current.get("task", {})

    values = {
        "main_intent": (
            legacy.get("main_intent"),
            current.get("main_intent"),
        ),
        "task_complexity": (
            legacy_task.get("complexity"),
            current_task.get("complexity"),
        ),
        "task_shape": (
            legacy_task.get("shape"),
            current_task.get("shape"),
        ),
        "task_topology": (
            infer_topology_from_legacy_task(legacy_task),
            current_task.get("topology"),
        ),
    }
    for field, (legacy_value, current_value) in values.items():
        if legacy_value is not None:
            distribution_counter["legacy"][field].update([legacy_value])
        if current_value is not None:
            distribution_counter["current"][field].update([current_value])


def check_distribution_drift(distribution_counter: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for field, legacy_counts in distribution_counter["legacy"].items():
        current_counts = distribution_counter["current"][field]
        legacy_total = sum(legacy_counts.values())
        current_total = sum(current_counts.values())
        labels = set(legacy_counts) | set(current_counts)
        for label in sorted(labels):
            legacy_ratio = legacy_counts.get(label, 0) / legacy_total if legacy_total else 0.0
            current_ratio = current_counts.get(label, 0) / current_total if current_total else 0.0
            delta = round(current_ratio - legacy_ratio, 4)
            if abs(delta) >= 0.2:
                warnings.append(
                    {
                        "kind": "distribution_drift",
                        "field": field,
                        "label": label,
                        "legacy_ratio": round(legacy_ratio, 4),
                        "current_ratio": round(current_ratio, 4),
                        "delta": delta,
                    }
                )
    return warnings


def write_gate_report(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(build_markdown_report(result), encoding="utf-8")


def build_markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# V2 Auto Quality Gate",
        "",
        f"- rows: `{result['rows']}`",
        f"- violations: `{result['violation_count']}`",
        f"- warnings: `{result['warning_count']}`",
        "",
        "## Violations",
        "",
    ]
    for item in result["violations"][:50]:
        lines.append(f"- `{item['row_id']}` `{item['kind']}` `{item['detail']}`")
    lines.extend(["", "## Warnings", ""])
    for item in result["warnings"][:50]:
        if item["kind"] == "distribution_drift":
            lines.append(
                f"- `{item['field']}` `{item['label']}` drift `{item['legacy_ratio']}` -> `{item['current_ratio']}`"
            )
        else:
            lines.append(f"- `{item}`")
    return "\n".join(lines) + "\n"


def _issue(row: dict[str, Any], kind: str, detail: str) -> dict[str, Any]:
    return {
        "row_id": row.get("id", ""),
        "batch": row.get("batch", ""),
        "kind": kind,
        "detail": detail,
    }


def main() -> int:
    args = parse_args()
    result = run_quality_gate(args.annotation_report_dir)
    write_gate_report(args.output_dir, result)
    print(
        json.dumps(
            {
                "annotation_report_dir": str(args.annotation_report_dir),
                "output_dir": str(args.output_dir),
                "rows": result["rows"],
                "violations": result["violation_count"],
                "warnings": result["warning_count"],
            },
            ensure_ascii=False,
        )
    )
    return 1 if result["violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
