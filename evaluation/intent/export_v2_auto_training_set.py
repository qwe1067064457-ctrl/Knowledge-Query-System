from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.intent.export_intent_training_set import (
    DEFAULT_DEV_DATASET_DIRS,
    DEFAULT_HELDOUT_DATASET_DIRS,
    DEFAULT_TRAIN_DATASET_DIRS,
    _infer_difficulty,
    _list_default_silver_dataset_dirs,
    write_training_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export auto-annotated V2 intent datasets into SFT-ready JSONL without touching V1 assets."
    )
    parser.add_argument("annotation_report_dir", type=Path)
    parser.add_argument("output_path", type=Path)
    return parser.parse_args()


def export_v2_auto_training_rows(annotation_report_dir: Path) -> list[dict[str, Any]]:
    dataset_split_map = _build_dataset_split_map()
    rows: list[dict[str, Any]] = []
    for path in sorted(annotation_report_dir.glob("*.jsonl")):
        dataset_name = path.stem
        split = dataset_split_map.get(dataset_name)
        if split is None:
            raise ValueError(f"Unknown dataset split for auto annotation report: {dataset_name}")
        is_heldout = split == "heldout"
        rows.extend(_export_dataset_rows(path, dataset_name=dataset_name, split=split, is_heldout=is_heldout))
    return rows


def _export_dataset_rows(path: Path, *, dataset_name: str, split: str, is_heldout: bool) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        exported.append(
            {
                "id": row["id"],
                "batch": row["batch"],
                "split": split,
                "input": row["input"],
                "evidence": row["gold"]["evidence"],
                "resolved": row["gold"]["resolved"],
                "control": row["gold"]["control"],
                "metadata": {
                    "source_dataset": dataset_name,
                    "source_query_id": row.get("source_query_id", ""),
                    "schema_version": "v2_auto",
                    "label_tier": row.get("label_tier", "gold"),
                    "label_source": row.get("label_source", "v2_auto_annotator"),
                    "review_status": row.get("review_status", "draft"),
                    "difficulty": _infer_difficulty(
                        {
                            "batch": row["batch"],
                            "gold": {"resolved": row["gold"]["resolved"]},
                        }
                    ),
                    "is_heldout": is_heldout,
                    "is_strict_rule_supervision": bool(
                        row["legacy_gold"].get("evidence", {}).get("rule_expectations")
                    ),
                    "is_auto_relabeled": True,
                    "review_required": bool(row.get("migration_review", {}).get("required", False)),
                },
            }
        )
    return exported


def _build_dataset_split_map() -> dict[str, str]:
    dataset_split_map: dict[str, str] = {}
    for path in DEFAULT_TRAIN_DATASET_DIRS:
        dataset_split_map[path.name] = "train"
    for path in _list_default_silver_dataset_dirs():
        dataset_split_map[path.name] = "train"
    for path in DEFAULT_DEV_DATASET_DIRS:
        dataset_split_map[path.name] = "dev"
    for path in DEFAULT_HELDOUT_DATASET_DIRS:
        dataset_split_map[path.name] = "heldout"
    return dataset_split_map


def main() -> int:
    args = parse_args()
    rows = export_v2_auto_training_rows(args.annotation_report_dir)
    write_training_jsonl(args.output_path, rows)
    print(
        json.dumps(
            {
                "annotation_report_dir": str(args.annotation_report_dir),
                "output_path": str(args.output_path),
                "rows": len(rows),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
