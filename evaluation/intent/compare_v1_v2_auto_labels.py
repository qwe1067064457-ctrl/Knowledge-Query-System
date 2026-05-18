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

from evaluation.intent.signal_taxonomy import EXPECTED_BUCKETS, flatten_signal_buckets, normalize_signal_buckets
from intent.task_compat import infer_topology_from_legacy_task

COMPARE_FIELDS = (
    "resolved.main_intent",
    "resolved.context_dependency",
    "resolved.task.complexity",
    "resolved.task.shape",
    "resolved.task.topology",
    "control.route",
    "control.mode",
    "resolved.modifiers.follow_up",
    "resolved.modifiers.challenge",
    "resolved.modifiers.soft_doubt",
    "resolved.modifiers.ask_source",
    "resolved.modifiers.ask_capability",
    "resolved.modifiers.scope_question",
    "resolved.modifiers.clarify_candidate",
    "resolved.modifiers.needs_clarification",
    "resolved.modifiers.out_of_scope",
    "resolved.ambiguity_state.clarify_candidate",
    "resolved.ambiguity_state.needs_context_check",
    "resolved.ambiguity_state.needs_previous_answer",
    "resolved.ambiguity_state.missing_reference_target",
    "resolved.ambiguity_state.possibly_ambiguous",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare V1 legacy labels with V2 auto annotations.")
    parser.add_argument("annotation_report_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args()


def build_diff_report(annotation_report_dir: Path) -> dict[str, Any]:
    dataset_summaries: list[dict[str, Any]] = []
    overall_rows: list[dict[str, Any]] = []

    for path in sorted(annotation_report_dir.glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        dataset_summary = summarize_rows(rows, dataset_name=path.stem)
        dataset_summaries.append(dataset_summary)
        overall_rows.extend(rows)

    overall_summary = summarize_rows(overall_rows, dataset_name="overall")
    return {
        "overall": overall_summary,
        "datasets": dataset_summaries,
    }


def summarize_rows(rows: list[dict[str, Any]], *, dataset_name: str) -> dict[str, Any]:
    signal_added = Counter()
    signal_removed = Counter()
    signal_bucket_added: dict[str, Counter[str]] = {bucket: Counter() for bucket in EXPECTED_BUCKETS}
    signal_bucket_removed: dict[str, Counter[str]] = {bucket: Counter() for bucket in EXPECTED_BUCKETS}
    field_changes = Counter()
    transition_counter = Counter()
    batch_counter = Counter()
    evidence_changed_rows = 0
    label_changed_rows = 0

    for row in rows:
        batch_counter.update([row.get("batch", "")])
        legacy_evidence = row.get("legacy_gold", {}).get("evidence", {})
        current_evidence = row.get("gold", {}).get("evidence", {})
        legacy_buckets = normalize_signal_buckets(legacy_evidence)
        current_buckets = normalize_signal_buckets(current_evidence)
        legacy_signals = set(flatten_signal_buckets(legacy_buckets))
        current_signals = set(flatten_signal_buckets(current_buckets))

        row_signal_changed = False
        for signal in sorted(current_signals - legacy_signals):
            signal_added.update([signal])
            row_signal_changed = True
        for signal in sorted(legacy_signals - current_signals):
            signal_removed.update([signal])
            row_signal_changed = True
        for bucket in EXPECTED_BUCKETS:
            legacy_bucket = set(legacy_buckets.get(bucket, []))
            current_bucket = set(current_buckets.get(bucket, []))
            for signal in sorted(current_bucket - legacy_bucket):
                signal_bucket_added[bucket].update([signal])
            for signal in sorted(legacy_bucket - current_bucket):
                signal_bucket_removed[bucket].update([signal])
        if row_signal_changed:
            evidence_changed_rows += 1

        changed_fields = compare_label_fields(row)
        if changed_fields:
            label_changed_rows += 1
            field_changes.update(changed_fields)
            for field in changed_fields:
                legacy_value, current_value = get_field_values(row, field)
                transition_counter.update([f"{field}:{legacy_value}->{current_value}"])

    return {
        "dataset": dataset_name,
        "rows": len(rows),
        "batches": dict(sorted(batch_counter.items())),
        "evidence_changed_rows": evidence_changed_rows,
        "label_changed_rows": label_changed_rows,
        "signal_added_counts": dict(sorted(signal_added.items())),
        "signal_removed_counts": dict(sorted(signal_removed.items())),
        "signal_bucket_added_counts": {
            bucket: dict(sorted(counter.items()))
            for bucket, counter in signal_bucket_added.items()
        },
        "signal_bucket_removed_counts": {
            bucket: dict(sorted(counter.items()))
            for bucket, counter in signal_bucket_removed.items()
        },
        "field_change_counts": dict(sorted(field_changes.items())),
        "top_transitions": [
            {"transition": key, "count": count}
            for key, count in transition_counter.most_common(20)
        ],
    }


def compare_label_fields(row: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for field in COMPARE_FIELDS:
        legacy_value, current_value = get_field_values(row, field)
        if legacy_value != current_value:
            changed.append(field)
    return changed


def get_field_values(row: dict[str, Any], field: str) -> tuple[Any, Any]:
    legacy_gold = row.get("legacy_gold", {})
    current_gold = row.get("gold", {})
    if field == "resolved.task.topology":
        legacy_task = legacy_gold.get("resolved", {}).get("task", {})
        current_task = current_gold.get("resolved", {}).get("task", {})
        return infer_topology_from_legacy_task(legacy_task), current_task.get("topology")

    legacy_value = _read_path(legacy_gold, field.removeprefix("resolved.") if field.startswith("resolved.") else field)
    current_value = _read_path(current_gold, field.removeprefix("resolved.") if field.startswith("resolved.") else field)
    if field.startswith("control."):
        legacy_value = _read_path(legacy_gold.get("control", {}), field.split(".", 1)[1])
        current_value = _read_path(current_gold.get("control", {}), field.split(".", 1)[1])
    elif field.startswith("resolved."):
        legacy_value = _read_path(legacy_gold.get("resolved", {}), field.split(".", 1)[1])
        current_value = _read_path(current_gold.get("resolved", {}), field.split(".", 1)[1])
    return legacy_value, current_value


def write_report(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(build_markdown_report(report), encoding="utf-8")


def build_markdown_report(report: dict[str, Any]) -> str:
    overall = report["overall"]
    lines = [
        "# V1 vs V2 Auto Label Diff",
        "",
        "## Overall",
        "",
        f"- rows: `{overall['rows']}`",
        f"- evidence_changed_rows: `{overall['evidence_changed_rows']}`",
        f"- label_changed_rows: `{overall['label_changed_rows']}`",
        "",
        "### Field Changes",
        "",
    ]
    for field, count in overall["field_change_counts"].items():
        lines.append(f"- `{field}`: `{count}`")
    lines.extend(["", "### Top Transitions", ""])
    for item in overall["top_transitions"]:
        lines.append(f"- `{item['transition']}`: `{item['count']}`")
    lines.extend(["", "## Per Dataset", ""])
    for dataset in report["datasets"]:
        lines.append(f"### {dataset['dataset']}")
        lines.append("")
        lines.append(f"- rows: `{dataset['rows']}`")
        lines.append(f"- evidence_changed_rows: `{dataset['evidence_changed_rows']}`")
        lines.append(f"- label_changed_rows: `{dataset['label_changed_rows']}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def _read_path(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def main() -> int:
    args = parse_args()
    report = build_diff_report(args.annotation_report_dir)
    write_report(args.output_dir, report)
    print(
        json.dumps(
            {
                "annotation_report_dir": str(args.annotation_report_dir),
                "output_dir": str(args.output_dir),
                "rows": report["overall"]["rows"],
                "label_changed_rows": report["overall"]["label_changed_rows"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
