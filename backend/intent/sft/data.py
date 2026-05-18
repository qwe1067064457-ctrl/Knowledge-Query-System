from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.intent.evaluate_intent_rules import load_dataset

DEFAULT_BOUNDARY_SIGNAL_LABELS = (
    "soft_doubt",
    "follow_up",
    "needs_clarification",
    "ask_source",
    "multi_question",
    "complex",
)

DEFAULT_TRAIN_DATASET_DIRS = (
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260514_gold_v1",
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260515_gold_v2",
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260516_gold_v1",
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260517_gold_v1",
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260518_gold_v1",
)
DEFAULT_SILVER_DATASET_ROOT = ROOT / "backend_test" / "intent" / "test_data" / "gold" / "silver"
DEFAULT_DEV_DATASET_DIRS = (
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "dev" / "seed_query_20260517_gold_v2",
)
DEFAULT_CALIBRATION_DATASET_DIRS = (
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "calibration" / "multisignal_20260517_v2",
)
DEFAULT_HELDOUT_DATASET_DIRS = (
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "frozen" / "frozen_heldout_v3",
)
DEFAULT_SPLITS = ("train", "dev", "calibration", "heldout")


@dataclass(frozen=True)
class MultiLabelExample:
    id: str
    text: str
    labels: list[int]
    active_labels: list[str]
    source_dataset: str
    label_tier: str
    split: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export multi-signal evidence rows for SFT.")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--train-dataset-dir", action="append", dest="train_dataset_dirs", type=Path, default=None)
    parser.add_argument("--silver-dataset-dir", action="append", dest="silver_dataset_dirs", type=Path, default=None)
    parser.add_argument("--dev-dataset-dir", action="append", dest="dev_dataset_dirs", type=Path, default=None)
    parser.add_argument("--calibration-dataset-dir", action="append", dest="calibration_dataset_dirs", type=Path, default=None)
    parser.add_argument("--heldout-dataset-dir", action="append", dest="heldout_dataset_dirs", type=Path, default=None)
    parser.add_argument("--signal-label", action="append", dest="signal_labels", default=None)
    parser.add_argument("--include-history", action="store_true")
    return parser.parse_args()


def export_signal_rows(
    *,
    train_dataset_dirs: list[Path] | None = None,
    silver_dataset_dirs: list[Path] | None = None,
    dev_dataset_dirs: list[Path] | None = None,
    calibration_dataset_dirs: list[Path] | None = None,
    heldout_dataset_dirs: list[Path] | None = None,
    signal_labels: list[str] | None = None,
    include_history: bool = False,
) -> dict[str, Any]:
    label_names = list(signal_labels or DEFAULT_BOUNDARY_SIGNAL_LABELS)
    train_dirs = list(DEFAULT_TRAIN_DATASET_DIRS) if train_dataset_dirs is None else list(train_dataset_dirs)
    silver_dirs = _list_default_silver_dataset_dirs() if silver_dataset_dirs is None else list(silver_dataset_dirs)
    dev_dirs = list(DEFAULT_DEV_DATASET_DIRS) if dev_dataset_dirs is None else list(dev_dataset_dirs)
    calibration_dirs = list(DEFAULT_CALIBRATION_DATASET_DIRS) if calibration_dataset_dirs is None else list(calibration_dataset_dirs)
    heldout_dirs = list(DEFAULT_HELDOUT_DATASET_DIRS) if heldout_dataset_dirs is None else list(heldout_dataset_dirs)

    rows_by_split = {split: [] for split in DEFAULT_SPLITS}
    for dataset_dir in train_dirs:
        rows_by_split["train"].extend(_export_dataset_dir(dataset_dir, split="train", label_names=label_names, include_history=include_history))
    for dataset_dir in silver_dirs:
        rows_by_split["train"].extend(_export_dataset_dir(dataset_dir, split="train", label_names=label_names, include_history=include_history))
    for dataset_dir in dev_dirs:
        rows_by_split["dev"].extend(_export_dataset_dir(dataset_dir, split="dev", label_names=label_names, include_history=include_history))
    for dataset_dir in calibration_dirs:
        rows_by_split["calibration"].extend(_export_dataset_dir(dataset_dir, split="calibration", label_names=label_names, include_history=include_history))
    for dataset_dir in heldout_dirs:
        rows_by_split["heldout"].extend(_export_dataset_dir(dataset_dir, split="heldout", label_names=label_names, include_history=include_history))

    return {
        "task_name": "required_signals_multilabel",
        "label_names": label_names,
        "rows_by_split": rows_by_split,
        "include_history": include_history,
        "label_group": "boundary_signals_v1",
    }


def build_query_text(input_block: dict[str, Any], *, include_history: bool = False) -> str:
    user_query = str(input_block.get("user_query", "")).strip()
    if not include_history:
        return user_query

    segments: list[str] = []
    history = input_block.get("history") or []
    if history:
        history_lines: list[str] = []
        for turn in history:
            role = str(turn.get("role", "unknown")).strip()
            content = str(turn.get("content", "")).strip()
            if content:
                history_lines.append(f"{role}: {content}")
        if history_lines:
            segments.append("[历史]\n" + "\n".join(history_lines))
    segments.append("[当前问题]\n" + user_query)
    return "\n\n".join(segment for segment in segments if segment)


def extract_required_signal_vector(evidence: dict[str, Any], *, label_names: list[str]) -> tuple[list[int], list[str]]:
    active = set(str(item) for item in evidence.get("required_signals", []))
    labels = [1 if label in active else 0 for label in label_names]
    active_labels = [label for label, value in zip(label_names, labels) if value]
    return labels, active_labels


def write_multilabel_bundle(output_dir: Path, bundle: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    label_map = {label: index for index, label in enumerate(bundle["label_names"])}
    (output_dir / "label_map.json").write_text(json.dumps(label_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for split, rows in bundle["rows_by_split"].items():
        _write_jsonl(output_dir / f"{split}.jsonl", rows)
    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "task_name": bundle["task_name"],
                "label_names": bundle["label_names"],
                "include_history": bundle["include_history"],
                "label_group": bundle.get("label_group", "boundary_signals_v1"),
                "summary": summarize_bundle(bundle),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_multilabel_bundle(bundle_dir: Path) -> dict[str, Any]:
    label_map_path = bundle_dir / "label_map.json"
    manifest_path = bundle_dir / "manifest.json"
    if not label_map_path.exists():
        raise FileNotFoundError(f"Missing label map: {label_map_path}")
    label_map = json.loads(label_map_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    label_names = [label for label, _ in sorted(label_map.items(), key=lambda item: item[1])]
    splits: dict[str, list[MultiLabelExample]] = {}
    for split in DEFAULT_SPLITS:
        split_path = bundle_dir / f"{split}.jsonl"
        if not split_path.exists():
            raise FileNotFoundError(f"Missing split file: {split_path}")
        splits[split] = _load_examples(split_path)
    return {
        "task_name": "required_signals_multilabel",
        "bundle_dir": bundle_dir,
        "label_names": label_names,
        "label_map": label_map,
        "splits": splits,
        "label_group": manifest.get("label_group", "boundary_signals_v1"),
        "include_history": bool(manifest.get("include_history", False)),
    }


def summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    rows_by_split = bundle["rows_by_split"] if "rows_by_split" in bundle else {
        split: [
            {
                "labels": row.labels,
                "active_labels": row.active_labels,
            }
            for row in rows
        ]
        for split, rows in bundle["splits"].items()
    }
    summary: dict[str, Any] = {}
    label_names = list(bundle["label_names"])
    for split, rows in rows_by_split.items():
        label_counter = Counter()
        for row in rows:
            for label in row["active_labels"]:
                label_counter[label] += 1
        summary[split] = {
            "rows": len(rows),
            "active_signal_counts": {label: label_counter.get(label, 0) for label in label_names},
        }
    return summary


def _export_dataset_dir(dataset_dir: Path, *, split: str, label_names: list[str], include_history: bool) -> list[dict[str, Any]]:
    rows = load_dataset(dataset_dir)
    dataset_name = dataset_dir.name
    exported: list[dict[str, Any]] = []
    for row in rows:
        labels, active_labels = extract_required_signal_vector(row["gold"]["evidence"], label_names=label_names)
        exported.append(
            {
                "id": row["id"],
                "text": build_query_text(row["input"], include_history=include_history),
                "labels": labels,
                "active_labels": active_labels,
                "source_dataset": dataset_name,
                "label_tier": row.get("label_tier", "gold"),
                "split": split,
            }
        )
    return exported


def _load_examples(path: Path) -> list[MultiLabelExample]:
    examples: list[MultiLabelExample] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        examples.append(
            MultiLabelExample(
                id=row["id"],
                text=row["text"],
                labels=[int(value) for value in row["labels"]],
                active_labels=[str(label) for label in row.get("active_labels", [])],
                source_dataset=row.get("source_dataset", ""),
                label_tier=row.get("label_tier", ""),
                split=row.get("split", path.stem),
            )
        )
    return examples


def _list_default_silver_dataset_dirs() -> list[Path]:
    if not DEFAULT_SILVER_DATASET_ROOT.exists():
        return []
    return sorted([path for path in DEFAULT_SILVER_DATASET_ROOT.iterdir() if path.is_dir()], key=lambda path: path.name)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def main() -> int:
    args = parse_args()
    bundle = export_signal_rows(
        train_dataset_dirs=args.train_dataset_dirs,
        silver_dataset_dirs=args.silver_dataset_dirs,
        dev_dataset_dirs=args.dev_dataset_dirs,
        calibration_dataset_dirs=args.calibration_dataset_dirs,
        heldout_dataset_dirs=args.heldout_dataset_dirs,
        signal_labels=args.signal_labels,
        include_history=args.include_history,
    )
    write_multilabel_bundle(args.output_dir, bundle)
    print(json.dumps({"output_dir": str(args.output_dir), "summary": summarize_bundle(bundle)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
