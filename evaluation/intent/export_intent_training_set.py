from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.intent.evaluate_intent_rules import load_dataset

DEFAULT_TRAIN_DATASET_DIRS = (
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260514_gold_v1",
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260515_gold_v2",
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260516_gold_v1",
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "train" / "seed_query_20260517_gold_v1",
)

DEFAULT_SILVER_DATASET_ROOT = ROOT / "backend_test" / "intent" / "test_data" / "gold" / "silver"

DEFAULT_DEV_DATASET_DIRS = (
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "dev" / "seed_query_20260515_gold_v1",
)

DEFAULT_HELDOUT_DATASET_DIRS = (
    ROOT / "backend_test" / "intent" / "test_data" / "gold" / "frozen" / "frozen_heldout_v2",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export intent four-layer datasets into SFT-ready JSONL.")
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--train-dataset-dir", action="append", dest="train_dataset_dirs", type=Path, default=None)
    parser.add_argument("--silver-dataset-dir", action="append", dest="silver_dataset_dirs", type=Path, default=None)
    parser.add_argument("--dev-dataset-dir", action="append", dest="dev_dataset_dirs", type=Path, default=None)
    parser.add_argument("--heldout-dataset-dir", action="append", dest="heldout_dataset_dirs", type=Path, default=None)
    return parser.parse_args()


def export_training_rows(
    *,
    train_dataset_dirs: list[Path] | None = None,
    silver_dataset_dirs: list[Path] | None = None,
    dev_dataset_dirs: list[Path] | None = None,
    heldout_dataset_dirs: list[Path] | None = None,
) -> list[dict[str, Any]]:
    use_defaults = (
        train_dataset_dirs is None
        and silver_dataset_dirs is None
        and dev_dataset_dirs is None
        and heldout_dataset_dirs is None
    )
    train_dirs = list(DEFAULT_TRAIN_DATASET_DIRS) if use_defaults else list(train_dataset_dirs or [])
    silver_dirs = _list_default_silver_dataset_dirs() if use_defaults else list(silver_dataset_dirs or [])
    dev_dirs = list(DEFAULT_DEV_DATASET_DIRS) if use_defaults else list(dev_dataset_dirs or [])
    heldout_dirs = list(DEFAULT_HELDOUT_DATASET_DIRS) if use_defaults else list(heldout_dataset_dirs or [])

    exported: list[dict[str, Any]] = []
    for dataset_dir in train_dirs:
        exported.extend(_export_dataset_dir(dataset_dir, split="train", is_heldout=False))
    for dataset_dir in silver_dirs:
        exported.extend(_export_dataset_dir(dataset_dir, split="train", is_heldout=False))
    for dataset_dir in dev_dirs:
        exported.extend(_export_dataset_dir(dataset_dir, split="dev", is_heldout=False))
    for dataset_dir in heldout_dirs:
        exported.extend(_export_dataset_dir(dataset_dir, split="heldout", is_heldout=True))
    return exported


def _list_default_silver_dataset_dirs() -> list[Path]:
    if not DEFAULT_SILVER_DATASET_ROOT.exists():
        return []
    return sorted(
        [path for path in DEFAULT_SILVER_DATASET_ROOT.iterdir() if path.is_dir()],
        key=lambda path: path.name,
    )


def write_training_jsonl(output_path: Path, rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _export_dataset_dir(dataset_dir: Path, *, split: str, is_heldout: bool) -> list[dict[str, Any]]:
    dataset_rows = load_dataset(dataset_dir)
    dataset_name = dataset_dir.name
    return [
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
                "label_tier": row.get("label_tier", "gold"),
                "label_source": row.get("label_source", "gold_dataset"),
                "review_status": row.get("review_status", "approved"),
                "difficulty": _infer_difficulty(row),
                "is_heldout": is_heldout,
                "is_strict_rule_supervision": bool(row["gold"]["evidence"].get("rule_expectations")),
            },
        }
        for row in dataset_rows
    ]


def _infer_difficulty(row: dict[str, Any]) -> str:
    batch = str(row["batch"])
    complexity = str(row["gold"]["resolved"]["task"]["complexity"])
    if complexity in {"complex", "compound"}:
        return "hard"
    if batch in {"soft_doubt_seed", "qa_judgment_seed", "soft_doubt_heldout", "qa_judgment_heldout", "follow_up", "meta", "mixed_intent", "fuzzy_qa"}:
        return "medium"
    return "easy"


def main() -> int:
    args = parse_args()
    rows = export_training_rows(
        train_dataset_dirs=args.train_dataset_dirs,
        silver_dataset_dirs=args.silver_dataset_dirs,
        dev_dataset_dirs=args.dev_dataset_dirs,
        heldout_dataset_dirs=args.heldout_dataset_dirs,
    )
    write_training_jsonl(args.output_path, rows)
    print(json.dumps({"output_path": str(args.output_path), "rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
