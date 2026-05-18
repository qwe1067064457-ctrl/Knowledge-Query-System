from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MAIN_INTENT_LABELS = (
    "qa",
    "chat",
    "system",
    "unsupported",
)

TASK_COMPLEXITY_LABELS = (
    "simple",
    "compound",
    "complex",
)

TASK_SHAPE_LABELS = (
    "single_question",
    "multi_question",
    "compare",
    "summarize",
    "extract",
    "verify",
    "mixed",
    "none",
)

TASK_TOPOLOGY_LABELS = (
    "single",
    "parallel_queries",
    "parallel_subtasks",
    "staged",
)

MODIFIER_NAMES = (
    "follow_up",
    "challenge",
    "soft_doubt",
    "ask_source",
    "ask_capability",
    "needs_clarification",
    "out_of_scope",
)

MULTICLASS_TASKS: dict[str, tuple[str, ...]] = {
    "main_intent": MAIN_INTENT_LABELS,
    "task_complexity": TASK_COMPLEXITY_LABELS,
    "task_shape": TASK_SHAPE_LABELS,
    "task_topology": TASK_TOPOLOGY_LABELS,
}

BINARY_TASKS: dict[str, str] = {
    "soft_doubt": "soft_doubt",
    **{f"modifier_{name}": name for name in MODIFIER_NAMES if name != "soft_doubt"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare MacBERT baseline datasets from exported intent JSONL.")
    parser.add_argument("input_jsonl", type=Path, help="Path to intent_training_v*.jsonl")
    parser.add_argument("output_dir", type=Path, help="Directory to write task-specific baseline datasets")
    return parser.parse_args()


def load_training_export(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def prepare_macbert_datasets(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped_outputs: dict[str, dict[str, list[dict[str, Any]]]] = {
        task_name: defaultdict(list)
        for task_name in (*BINARY_TASKS.keys(), *MULTICLASS_TASKS.keys())
    }

    for row in rows:
        split = row["split"]
        text = _build_model_text(row["input"])
        metadata = row.get("metadata", {})
        resolved = row.get("resolved", {})
        modifiers = resolved.get("modifiers", {})
        task = resolved.get("task", {})
        base_fields = {
            "id": row["id"],
            "text": text,
            "source_dataset": metadata.get("source_dataset", ""),
            "label_tier": metadata.get("label_tier", "gold"),
        }

        for task_name, modifier_name in BINARY_TASKS.items():
            value = bool(modifiers.get(modifier_name, False))
            grouped_outputs[task_name][split].append(
                {
                    **base_fields,
                    "label": int(value),
                    "label_name": "true" if value else "false",
                }
            )

        multiclass_values = {
            "main_intent": resolved.get("main_intent", ""),
            "task_complexity": task.get("complexity", ""),
            "task_shape": task.get("shape", ""),
            "task_topology": task.get("topology", ""),
        }
        for task_name, labels in MULTICLASS_TASKS.items():
            value = str(multiclass_values.get(task_name, ""))
            if value not in labels:
                continue
            grouped_outputs[task_name][split].append(
                {
                    **base_fields,
                    "label": labels.index(value),
                    "label_name": value,
                }
            )

    summary = {
        task_name: _summarize_task(grouped_outputs[task_name])
        for task_name in grouped_outputs
    }
    return {
        "datasets": grouped_outputs,
        "summary": summary,
        "label_maps": {
            **{task_name: {"false": 0, "true": 1} for task_name in BINARY_TASKS},
            **{task_name: {label: idx for idx, label in enumerate(labels)} for task_name, labels in MULTICLASS_TASKS.items()},
        },
    }


def write_macbert_datasets(output_dir: Path, prepared: dict[str, Any], *, source_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for task_name, split_rows in prepared["datasets"].items():
        task_dir = output_dir / task_name
        task_dir.mkdir(parents=True, exist_ok=True)
        for split in ("train", "dev", "heldout"):
            rows = split_rows.get(split, [])
            _write_jsonl(task_dir / f"{split}.jsonl", rows)
        (task_dir / "label_map.json").write_text(
            json.dumps(prepared["label_maps"][task_name], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (task_dir / "README.md").write_text(
            _build_task_readme(
                task_name=task_name,
                label_map=prepared["label_maps"][task_name],
                summary=prepared["summary"][task_name],
                source_path=source_path,
            ),
            encoding="utf-8",
        )
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "source_path": str(source_path),
                "tasks": prepared["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _build_model_text(input_block: dict[str, Any]) -> str:
    history = input_block.get("history", [])
    segments: list[str] = []
    if history:
        history_lines = []
        for turn in history:
            role = turn.get("role", "unknown")
            content = str(turn.get("content", "")).strip()
            if content:
                history_lines.append(f"{role}: {content}")
        if history_lines:
            segments.append("[历史]\n" + "\n".join(history_lines))
    user_query = str(input_block.get("user_query", "")).strip()
    segments.append("[当前问题]\n" + user_query)
    return "\n\n".join(segment for segment in segments if segment).strip()


def _summarize_task(split_rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    by_split: dict[str, Any] = {}
    for split, rows in split_rows.items():
        label_counter = Counter(row["label_name"] for row in rows)
        by_split[split] = {
            "rows": len(rows),
            "labels": dict(sorted(label_counter.items())),
        }
    return by_split


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _build_task_readme(*, task_name: str, label_map: dict[str, int], summary: dict[str, Any], source_path: Path) -> str:
    lines = [
        f"# MacBERT Baseline Dataset: {task_name}",
        "",
        f"- source export: `{source_path}`",
        "- model family: `hfl/chinese-macbert-base`",
        "- format: one JSONL per split, each row contains `id / text / label / label_name / source_dataset / label_tier`",
        "",
        "## Label Map",
        "",
        "```json",
        json.dumps(label_map, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Split Summary",
        "",
    ]
    for split, payload in summary.items():
        lines.append(f"### {split}")
        lines.append("")
        lines.append(f"- rows: `{payload['rows']}`")
        lines.append(f"- labels: `{json.dumps(payload['labels'], ensure_ascii=False)}`")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    rows = load_training_export(args.input_jsonl)
    prepared = prepare_macbert_datasets(rows)
    write_macbert_datasets(args.output_dir, prepared, source_path=args.input_jsonl)
    print(
        json.dumps(
            {
                "source_path": str(args.input_jsonl),
                "output_dir": str(args.output_dir),
                "summary": prepared["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
