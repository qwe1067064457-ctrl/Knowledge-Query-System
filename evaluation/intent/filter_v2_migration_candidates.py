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
from evaluation.intent.v2_migration import review_reasons_for_v2, should_review_for_v2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select high-risk V2 migration candidates from V1 intent datasets.")
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("output_path", type=Path)
    return parser.parse_args()


def select_v2_migration_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if not should_review_for_v2(row):
            continue
        copied = dict(row)
        copied["migration_review"] = {
            "required": True,
            "reasons": review_reasons_for_v2(row),
        }
        selected.append(copied)
    return selected


def write_candidates(output_path: Path, rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    rows = load_dataset(args.dataset_dir)
    selected = select_v2_migration_candidates(rows)
    write_candidates(args.output_path, selected)
    print(json.dumps({"dataset_dir": str(args.dataset_dir), "selected": len(selected)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
