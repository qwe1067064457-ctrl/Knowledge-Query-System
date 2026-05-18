from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
BACKEND_DIR = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from intent.sft.v2.v2_label_spaces import DEFAULT_LABEL_SPACES, MULTICLASS_HEADS, MULTILABEL_HEADS, build_label_space_manifest, label_to_index

DEFAULT_TOPOLOGY_EXPORT_PATH = ROOT / "evaluation" / "intent" / "exports" / "v2" / "intent_training_v2_topology_20260518.jsonl"
DEFAULT_AUTO_EXPORT_PATH = ROOT / "evaluation" / "intent" / "exports" / "v2" / "intent_training_v2_auto_20260518.jsonl"
DEFAULT_V2_SPLITS = ("train", "dev", "heldout")


@dataclass(frozen=True)
class V2Example:
    id: str
    text: str
    split: str
    source_dataset: str
    label_tier: str
    main_intent: int
    task_complexity: int
    task_shape: int
    task_topology: int
    modifiers: list[int]
    context: list[int]
    safety: list[int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export V2 intent understanding rows into a multitask SFT bundle.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--input-jsonl", action="append", dest="input_jsonl_paths", type=Path, default=None)
    parser.add_argument("--include-history", action="store_true")
    parser.add_argument("--dedupe", choices=("error", "first", "last"), default="error")
    return parser.parse_args()


def export_v2_rows(
    *,
    input_jsonl_paths: list[Path] | None = None,
    include_history: bool = False,
    dedupe: str = "error",
) -> dict[str, Any]:
    input_paths = list(input_jsonl_paths) if input_jsonl_paths is not None else [DEFAULT_TOPOLOGY_EXPORT_PATH]
    rows_by_split: dict[str, list[dict[str, Any]]] = {split: [] for split in DEFAULT_V2_SPLITS}
    seen_ids: dict[str, tuple[str, int]] = {}

    for path_index, input_path in enumerate(input_paths):
        for row in _read_jsonl(input_path):
            exported = _export_row(row, include_history=include_history)
            if exported["split"] not in rows_by_split:
                continue
            row_id = exported["id"]
            if row_id in seen_ids:
                previous_split, previous_path_index = seen_ids[row_id]
                if dedupe == "error":
                    raise ValueError(f"Duplicate row id `{row_id}` across V2 sources")
                if dedupe == "first":
                    continue
                if dedupe == "last":
                    rows_by_split[previous_split] = [item for item in rows_by_split[previous_split] if item["id"] != row_id]
            rows_by_split[exported["split"]].append(exported)
            seen_ids[row_id] = (exported["split"], path_index)

    return {
        "task_name": "intent_v2_multitask",
        "rows_by_split": rows_by_split,
        "include_history": include_history,
        "label_spaces": build_label_space_manifest(),
    }


def write_v2_bundle(output_dir: Path, bundle: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "label_spaces.json").write_text(
        json.dumps(bundle["label_spaces"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for split, rows in bundle["rows_by_split"].items():
        _write_jsonl(output_dir / f"{split}.jsonl", rows)
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "task_name": bundle["task_name"],
                "include_history": bundle["include_history"],
                "label_spaces": bundle["label_spaces"],
                "summary": summarize_v2_bundle(bundle),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_v2_bundle(bundle_dir: Path) -> dict[str, Any]:
    label_spaces_path = bundle_dir / "label_spaces.json"
    manifest_path = bundle_dir / "manifest.json"
    if not label_spaces_path.exists():
        raise FileNotFoundError(f"Missing label spaces: {label_spaces_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    label_spaces = json.loads(label_spaces_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    splits: dict[str, list[V2Example]] = {}
    for split in DEFAULT_V2_SPLITS:
        split_path = bundle_dir / f"{split}.jsonl"
        if not split_path.exists():
            raise FileNotFoundError(f"Missing split file: {split_path}")
        splits[split] = _load_examples(split_path)
    return {
        "task_name": manifest["task_name"],
        "bundle_dir": bundle_dir,
        "include_history": bool(manifest.get("include_history", False)),
        "label_spaces": label_spaces,
        "splits": splits,
    }


def summarize_v2_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    rows_by_split = bundle["rows_by_split"] if "rows_by_split" in bundle else {
        split: [_serialize_example(example) for example in rows]
        for split, rows in bundle["splits"].items()
    }
    summary: dict[str, Any] = {}
    for split, rows in rows_by_split.items():
        main_intent = Counter()
        task_complexity = Counter()
        task_shape = Counter()
        task_topology = Counter()
        modifiers = Counter()
        context = Counter()
        safety = Counter()
        for row in rows:
            main_intent.update([row["targets"]["main_intent"]])
            task_complexity.update([row["targets"]["task_complexity"]])
            task_shape.update([row["targets"]["task_shape"]])
            task_topology.update([row["targets"]["task_topology"]])
            modifiers.update(row["targets"]["modifiers_active"])
            context.update(row["targets"]["context_active"])
            safety.update(row["targets"]["safety_active"])
        summary[split] = {
            "rows": len(rows),
            "main_intent_counts": dict(sorted(main_intent.items())),
            "task_complexity_counts": dict(sorted(task_complexity.items())),
            "task_shape_counts": dict(sorted(task_shape.items())),
            "task_topology_counts": dict(sorted(task_topology.items())),
            "modifier_counts": dict(sorted(modifiers.items())),
            "context_counts": dict(sorted(context.items())),
            "safety_counts": dict(sorted(safety.items())),
        }
    return summary


def build_v2_text(input_block: dict[str, Any], *, include_history: bool = False) -> str:
    user_query = str(input_block.get("user_query", "")).strip()
    if not include_history:
        return user_query

    history = input_block.get("history") or []
    parts: list[str] = []
    if history:
        lines: list[str] = []
        for turn in history:
            role = str(turn.get("role", "unknown")).strip()
            content = str(turn.get("content", "")).strip()
            if content:
                lines.append(f"{role}: {content}")
        if lines:
            parts.append("[历史]\n" + "\n".join(lines))
    parts.append("[当前问题]\n" + user_query)
    return "\n\n".join(part for part in parts if part)


def _export_row(row: dict[str, Any], *, include_history: bool) -> dict[str, Any]:
    payload = _unwrap_v2_payload(row)
    metadata = payload.get("metadata", {})
    resolved = payload["resolved"]
    evidence = payload["evidence"]
    context_signals = evidence.get("context_signals", {})
    signal_buckets = evidence.get("signal_buckets", {})

    main_intent = _require_label(resolved.get("main_intent"), MULTICLASS_HEADS["main_intent"], "main_intent", row.get("id", ""))
    task = resolved.get("task", {})
    task_complexity = _require_label(task.get("complexity"), MULTICLASS_HEADS["task_complexity"], "task_complexity", row.get("id", ""))
    task_shape = _require_label(task.get("shape"), MULTICLASS_HEADS["task_shape"], "task_shape", row.get("id", ""))
    task_topology = _require_label(task.get("topology"), MULTICLASS_HEADS["task_topology"], "task_topology", row.get("id", ""))

    modifiers_payload = resolved.get("modifiers", {})
    modifiers = _multilabel_vector_from_mapping(modifiers_payload, MULTILABEL_HEADS["modifiers"])
    context_mapping = {
        "history_reference": bool(context_signals.get("history_reference", False)),
        "needs_previous_answer": bool(
            context_signals.get("needs_previous_answer", False) or context_signals.get("previous_answer", False)
        ),
        "previous_retrieval": bool(context_signals.get("previous_retrieval", False)),
        "clarify_hint": bool(context_signals.get("clarify_hint", False) or context_signals.get("ambiguous", False)),
    }
    context = _multilabel_vector_from_mapping(context_mapping, MULTILABEL_HEADS["context"])
    safety_mapping = {
        "unsupported": "unsupported" in (signal_buckets.get("safety") or []) or resolved.get("main_intent") == "unsupported",
        "out_of_scope": bool(resolved.get("modifiers", {}).get("out_of_scope", False)),
    }
    safety = _multilabel_vector_from_mapping(safety_mapping, MULTILABEL_HEADS["safety"])

    split = str(row.get("split") or metadata.get("split") or _infer_split(metadata)).strip()
    if split == "calibration":
        split = "dev"

    return {
        "id": row["id"],
        "text": build_v2_text(row.get("input", {}), include_history=include_history),
        "split": split,
        "source_dataset": metadata.get("source_dataset", ""),
        "label_tier": metadata.get("label_tier", row.get("label_tier", "gold")),
        "targets": {
            "main_intent": main_intent,
            "task_complexity": task_complexity,
            "task_shape": task_shape,
            "task_topology": task_topology,
            "modifiers": modifiers,
            "modifiers_active": _active_labels(modifiers, MULTILABEL_HEADS["modifiers"]),
            "context": context,
            "context_active": _active_labels(context, MULTILABEL_HEADS["context"]),
            "safety": safety,
            "safety_active": _active_labels(safety, MULTILABEL_HEADS["safety"]),
        },
    }


def _unwrap_v2_payload(row: dict[str, Any]) -> dict[str, Any]:
    if "gold" in row and isinstance(row["gold"], dict):
        payload = dict(row["gold"])
        payload["metadata"] = dict(row.get("gold", {}).get("metadata", {}))
        if not payload["metadata"]:
            payload["metadata"] = {
                "source_dataset": row.get("metadata", {}).get("source_dataset", ""),
                "label_tier": row.get("metadata", {}).get("label_tier", row.get("label_tier", "gold")),
                "is_heldout": row.get("metadata", {}).get("is_heldout", False),
            }
        return payload
    return row


def _infer_split(metadata: dict[str, Any]) -> str:
    if metadata.get("is_heldout"):
        return "heldout"
    return "train"


def _require_label(value: Any, label_space: tuple[str, ...], field_name: str, row_id: str) -> str:
    label = str(value)
    if label not in label_space:
        raise ValueError(f"Unknown {field_name} `{label}` for row `{row_id}`")
    return label


def _multilabel_vector_from_mapping(mapping: dict[str, Any], labels: tuple[str, ...]) -> list[int]:
    return [1 if bool(mapping.get(label, False)) else 0 for label in labels]


def _active_labels(values: list[int], labels: tuple[str, ...]) -> list[str]:
    return [label for label, value in zip(labels, values) if value]


def _load_examples(path: Path) -> list[V2Example]:
    multiclass_indices = {name: label_to_index(labels) for name, labels in MULTICLASS_HEADS.items()}
    examples: list[V2Example] = []
    for row in _read_jsonl(path):
        targets = row["targets"]
        examples.append(
            V2Example(
                id=row["id"],
                text=row["text"],
                split=row["split"],
                source_dataset=row.get("source_dataset", ""),
                label_tier=row.get("label_tier", "gold"),
                main_intent=multiclass_indices["main_intent"][targets["main_intent"]],
                task_complexity=multiclass_indices["task_complexity"][targets["task_complexity"]],
                task_shape=multiclass_indices["task_shape"][targets["task_shape"]],
                task_topology=multiclass_indices["task_topology"][targets["task_topology"]],
                modifiers=[int(value) for value in targets["modifiers"]],
                context=[int(value) for value in targets["context"]],
                safety=[int(value) for value in targets["safety"]],
            )
        )
    return examples


def _serialize_example(example: V2Example) -> dict[str, Any]:
    return {
        "id": example.id,
        "text": example.text,
        "split": example.split,
        "source_dataset": example.source_dataset,
        "label_tier": example.label_tier,
        "targets": {
            "main_intent": MULTICLASS_HEADS["main_intent"][example.main_intent],
            "task_complexity": MULTICLASS_HEADS["task_complexity"][example.task_complexity],
            "task_shape": MULTICLASS_HEADS["task_shape"][example.task_shape],
            "task_topology": MULTICLASS_HEADS["task_topology"][example.task_topology],
            "modifiers": example.modifiers,
            "modifiers_active": _active_labels(example.modifiers, MULTILABEL_HEADS["modifiers"]),
            "context": example.context,
            "context_active": _active_labels(example.context, MULTILABEL_HEADS["context"]),
            "safety": example.safety,
            "safety_active": _active_labels(example.safety, MULTILABEL_HEADS["safety"]),
        },
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    bundle = export_v2_rows(
        input_jsonl_paths=args.input_jsonl_paths,
        include_history=args.include_history,
        dedupe=args.dedupe,
    )
    write_v2_bundle(args.output_dir, bundle)
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "summary": summarize_v2_bundle(bundle),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
