from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from intent import classify_intent  # noqa: E402

from evaluation.intent.evaluate_intent_rules import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-uplift campaign datasets into four-layer silver datasets.")
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args()


def auto_uplift_campaign_dataset(*, source_dir: Path, output_dir: Path) -> dict[str, int | str]:
    rows = load_dataset(source_dir)
    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped_corrupted = 0

    for row in rows:
        silver_row = _build_silver_row(row, source_dataset=source_dir.name)
        if silver_row is None:
            skipped_corrupted += 1
            continue
        grouped_rows[silver_row["batch"]].append(silver_row)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_readme(
        output_dir,
        source_dir.name,
        sum(len(items) for items in grouped_rows.values()),
        len(grouped_rows),
        skipped_corrupted=skipped_corrupted,
    )
    for batch, batch_rows in sorted(grouped_rows.items()):
        path = output_dir / f"{batch}.json"
        path.write_text(json.dumps(batch_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "rows": sum(len(items) for items in grouped_rows.values()),
        "batches": len(grouped_rows),
        "skipped_corrupted": skipped_corrupted,
    }


def _build_silver_row(row: dict[str, Any], *, source_dataset: str) -> dict[str, Any] | None:
    row_id = str(row.get("id", "")).strip()
    batch = str(row.get("batch", "")).strip()
    input_payload = row.get("input") or {}
    user_query = str(input_payload.get("user_query", "")).strip()
    history = input_payload.get("history") or []
    if not row_id:
        raise ValueError("campaign row missing id")
    if not batch:
        raise ValueError(f"campaign row {row_id} missing batch")
    if not user_query:
        raise ValueError(f"campaign row {row_id} missing input.user_query")
    if _looks_corrupted_query(user_query):
        return None

    analysis = classify_intent(user_query, history)
    required_rule_ids = [match.rule_id for match in analysis.evidence.matched_rules]
    rule_expectations = {rule_id: True for rule_id in required_rule_ids}
    required_signals = list(analysis.evidence.raw_signals)

    return {
        "id": row_id,
        "batch": batch,
        "input": {
            "user_query": user_query,
            "history": history,
        },
        "gold": {
            "evidence": {
                "classifier_mode": analysis.evidence.classifier_mode,
                "required_signals": required_signals,
                "required_rule_ids": required_rule_ids,
                "rule_expectations": rule_expectations,
                "unsupported_signals": dict(analysis.evidence.unsupported_signals),
                "dependency_signals": dict(analysis.evidence.dependency_signals),
            },
            "resolved": {
                "main_intent": analysis.resolved.main_intent,
                "modifiers": analysis.resolved.modifiers.to_dict(),
                "task": {
                    "complexity": analysis.resolved.task.complexity,
                    "shape": analysis.resolved.task.shape,
                },
                "context_dependency": analysis.resolved.context_dependency,
            },
            "control": {
                "route": analysis.control.route,
                "mode": analysis.control.mode,
            },
        },
        "label_tier": "silver",
        "label_source": "auto_uplift_rule_pipeline",
        "review_status": "draft",
        "notes": (
            f"auto uplifted from campaign dataset {source_dataset}; "
            f"existing campaign gold is ignored and current rule pipeline output is used"
        ),
        "source_query_id": row.get("source_query_id") or row_id,
        "source_dataset": source_dataset,
    }


def _write_readme(output_dir: Path, source_dataset: str, row_count: int, batch_count: int, *, skipped_corrupted: int) -> None:
    content = "\n".join(
        [
            f"# {output_dir.name}",
            "",
            "This dataset is an auto-uplifted silver dataset.",
            "",
            f"- source campaign: `{source_dataset}`",
            f"- rows: `{row_count}`",
            f"- batches: `{batch_count}`",
            f"- skipped_corrupted: `{skipped_corrupted}`",
            "- label tier: `silver`",
            "- label source: `auto_uplift_rule_pipeline`",
            "",
            "Notes:",
            "- input is copied from the campaign sample",
            "- four-layer fields are regenerated from the current classifier, resolver, and control pipeline",
            "- this dataset can be used for train-time expansion, not as frozen benchmark",
        ]
    )
    (output_dir / "README.md").write_text(content + "\n", encoding="utf-8")


def _looks_corrupted_query(user_query: str) -> bool:
    stripped = "".join(ch for ch in user_query if not ch.isspace())
    return bool(stripped) and set(stripped) <= {"?", "？"}


def main() -> int:
    args = parse_args()
    summary = auto_uplift_campaign_dataset(source_dir=args.source_dir, output_dir=args.output_dir)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
