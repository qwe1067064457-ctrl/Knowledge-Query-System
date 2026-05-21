from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BACKFILL_DIR = ROOT / "evaluation" / "intent" / "v2_sft" / "benchmark_backfill_20260519"
DEFAULT_OUTPUT_DIR = ROOT / "evaluation" / "intent" / "v2_sft" / "benchmark_ready_20260519"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze benchmark backfill candidates into auto-ready manifests.")
    parser.add_argument("--backfill-dir", type=Path, default=DEFAULT_BACKFILL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def _load_backfill(backfill_dir: Path) -> dict[str, Any]:
    split_manifest = json.loads((backfill_dir / "split_manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((backfill_dir / "summary.json").read_text(encoding="utf-8"))
    review_rows = _read_jsonl(backfill_dir / "review_candidates.jsonl")
    promotion_rows = _read_jsonl(backfill_dir / "promotion_candidates.jsonl")
    synthetic_rows = _read_jsonl(backfill_dir / "synthetic_candidates.jsonl")
    return {
        "split_manifest": split_manifest,
        "summary": summary,
        "review_rows": review_rows,
        "promotion_rows": promotion_rows,
        "synthetic_rows": synthetic_rows,
    }


def _read_export_rows(path: Path) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in _read_jsonl(path)}


def _freeze_gold_manifest(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    frozen_entries: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for entry in entries:
        status = "auto_frozen_legacy_seed" if entry["status"] == "legacy_seed" else "auto_frozen_gold_candidate"
        frozen_entries.append(
            {
                "id": entry["id"],
                "split": entry["split"],
                "status": status,
                "source_dataset": entry["source_dataset"],
                "label_tier": entry["label_tier"],
                "origin": "split_manifest",
                "reason": entry["reason"],
            }
        )
        decisions.append(
            {
                "id": entry["id"],
                "decision": "accept_gold_like",
                "target_manifest": "gold_only",
                "split": entry["split"],
                "source_dataset": entry["source_dataset"],
                "label_tier": entry["label_tier"],
            }
        )
    return frozen_entries, decisions


def _freeze_expanded_manifest(
    base_entries: list[dict[str, Any]],
    promotion_rows: list[dict[str, Any]],
    synthetic_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    frozen_entries = list(base_entries)
    decisions: list[dict[str, Any]] = []
    existing_ids = {entry["id"] for entry in frozen_entries}

    for row in promotion_rows:
        if row["id"] in existing_ids:
            continue
        frozen_entries.append(
            {
                "id": row["id"],
                "split": row["proposed_split"],
                "status": "auto_frozen_promotion_candidate",
                "source_dataset": row["source_dataset"],
                "label_tier": row["label_tier"],
                "origin": "promotion_candidates",
                "reason": ",".join(row["gap_features"]),
            }
        )
        decisions.append(
            {
                "id": row["id"],
                "decision": "accept_auto_promotion",
                "target_manifest": "expanded",
                "split": row["proposed_split"],
                "source_dataset": row["source_dataset"],
                "label_tier": row["label_tier"],
                "gap_features": row["gap_features"],
            }
        )
        existing_ids.add(row["id"])

    for row in synthetic_rows:
        if row["id"] in existing_ids:
            continue
        frozen_entries.append(
            {
                "id": row["id"],
                "split": row["proposed_split"],
                "status": "auto_frozen_synthetic_candidate",
                "source_dataset": row["source_dataset"],
                "label_tier": row["label_tier"],
                "origin": "synthetic_candidates",
                "reason": ",".join(row["gap_features"]),
            }
        )
        decisions.append(
            {
                "id": row["id"],
                "decision": "accept_synthetic_gap_fill",
                "target_manifest": "expanded",
                "split": row["proposed_split"],
                "source_dataset": row["source_dataset"],
                "label_tier": row["label_tier"],
                "gap_features": row["gap_features"],
                "template_kind": row.get("template_kind"),
            }
        )
        existing_ids.add(row["id"])

    return frozen_entries, decisions


def _build_context_signals(labels: dict[str, Any]) -> dict[str, bool]:
    context = set(labels.get("context", []))
    return {
        "history_reference": "history_reference" in context,
        "needs_previous_answer": "needs_previous_answer" in context,
        "previous_answer": "needs_previous_answer" in context,
        "previous_retrieval": "previous_retrieval" in context,
        "clarify_hint": "clarify_hint" in context,
        "ambiguous": "clarify_hint" in context,
    }


def _build_modifier_mapping(labels: dict[str, Any]) -> dict[str, bool]:
    active = set(labels.get("modifiers", []))
    modifier_names = (
        "follow_up",
        "challenge",
        "soft_doubt",
        "ask_source",
        "ask_capability",
        "needs_clarification",
        "out_of_scope",
    )
    return {name: name in active for name in modifier_names}


def _build_route(labels: dict[str, Any]) -> str:
    if labels.get("main_intent") == "chat":
        return "chat"
    if labels.get("main_intent") == "system":
        return "system"
    if labels.get("main_intent") == "unsupported":
        return "blocked"
    if labels.get("task_topology") in {"staged", "parallel_subtasks"}:
        return "orchestrated"
    return "rag"


def _build_mode(labels: dict[str, Any]) -> str:
    if "challenge" in labels.get("modifiers", []):
        return "challenge"
    if "ask_source" in labels.get("modifiers", []):
        return "source_check"
    if "needs_clarification" in labels.get("modifiers", []):
        return "clarify"
    return "normal"


def _materialize_promotion_row(row: dict[str, Any], auto_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    base_row = json.loads(json.dumps(auto_rows[row["id"]]))
    base_row["split"] = row["proposed_split"]
    metadata = base_row.setdefault("metadata", {})
    metadata["source_dataset"] = row["source_dataset"]
    metadata["label_tier"] = row["label_tier"]
    return base_row


def _materialize_synthetic_row(row: dict[str, Any]) -> dict[str, Any]:
    labels = row["proposed_labels"]
    modifier_mapping = _build_modifier_mapping(labels)
    unsupported = labels.get("main_intent") == "unsupported"
    out_of_scope = modifier_mapping.get("out_of_scope", False)
    return {
        "id": row["id"],
        "split": row["proposed_split"],
        "input": {
            "user_query": row["text"],
            "history": [],
        },
        "evidence": {
            "signal_buckets": {
                "intent": [labels["main_intent"]] if labels["main_intent"] in {"qa", "chat", "system"} else [],
                "task": [],
                "context": [],
                "safety": [label for label, active in {"unsupported": unsupported, "out_of_scope": out_of_scope}.items() if active],
            },
            "context_signals": _build_context_signals(labels),
        },
        "resolved": {
            "main_intent": labels["main_intent"],
            "modifiers": modifier_mapping,
            "task": {
                "complexity": labels["task_complexity"],
                "shape": labels["task_shape"],
                "topology": labels["task_topology"],
            },
            "context_dependency": "needs_previous_answer" if "needs_previous_answer" in labels.get("context", []) else "none",
        },
        "control": {
            "route": _build_route(labels),
            "mode": _build_mode(labels),
        },
        "metadata": {
            "source_dataset": row["source_dataset"],
            "label_tier": row["label_tier"],
            "is_heldout": row["proposed_split"] == "heldout",
        },
        "notes": f"synthetic benchmark candidate {row.get('template_kind', '')}".strip(),
    }


def build_freeze_pack(backfill_dir: Path) -> dict[str, Any]:
    payload = _load_backfill(backfill_dir)
    topology_export_path = Path(payload["summary"]["input_files"]["topology_export"])
    auto_export_path = Path(payload["summary"]["input_files"]["auto_export"])
    auto_export_rows = _read_export_rows(auto_export_path)
    split_entries = payload["split_manifest"]["entries"]
    gold_entries, gold_decisions = _freeze_gold_manifest(split_entries)
    expanded_entries, expanded_decisions = _freeze_expanded_manifest(
        base_entries=gold_entries,
        promotion_rows=payload["promotion_rows"],
        synthetic_rows=payload["synthetic_rows"],
    )
    expanded_override_rows = [
        _materialize_promotion_row(row, auto_export_rows)
        for row in payload["promotion_rows"]
    ] + [
        _materialize_synthetic_row(row)
        for row in payload["synthetic_rows"]
    ]

    summary = {
        "version": "2026-05-19",
        "task": "v2_benchmark_auto_freeze",
        "source_backfill_dir": str(backfill_dir),
        "gold_only": {
            "entries": len(gold_entries),
            "dev": sum(1 for entry in gold_entries if entry["split"] == "dev"),
            "calibration": sum(1 for entry in gold_entries if entry["split"] == "calibration"),
            "heldout": sum(1 for entry in gold_entries if entry["split"] == "heldout"),
        },
        "expanded": {
            "entries": len(expanded_entries),
            "dev": sum(1 for entry in expanded_entries if entry["split"] == "dev"),
            "calibration": sum(1 for entry in expanded_entries if entry["split"] == "calibration"),
            "heldout": sum(1 for entry in expanded_entries if entry["split"] == "heldout"),
        },
        "decision_counts": {
            "accept_gold_like": len(gold_decisions),
            "accept_auto_promotion": len([item for item in expanded_decisions if item["decision"] == "accept_auto_promotion"]),
            "accept_synthetic_gap_fill": len([item for item in expanded_decisions if item["decision"] == "accept_synthetic_gap_fill"]),
        },
        "boundary": {
            "gold_only_is_higher_confidence": True,
            "expanded_contains_auto_and_synthetic": True,
            "formal_human_review_still_required_for_official_benchmark": True,
        },
        "helper_files": {
            "topology_export": str(topology_export_path),
            "auto_export": str(auto_export_path),
            "expanded_override_rows": "expanded_override_rows.jsonl",
        },
    }

    return {
        "gold_manifest": {
            "version": "2026-05-19",
            "task": "v2_benchmark_auto_freeze_gold_only",
            "entries": gold_entries,
        },
        "expanded_manifest": {
            "version": "2026-05-19",
            "task": "v2_benchmark_auto_freeze_expanded",
            "entries": expanded_entries,
        },
        "decision_log": gold_decisions + expanded_decisions,
        "expanded_override_rows": expanded_override_rows,
        "summary": summary,
    }


def _build_readme(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V2 Benchmark Ready 20260519",
            "",
            "## 定位",
            "",
            "- 这是自动冻结产物，不是正式人工 reviewed benchmark。",
            "- `gold_manifest.json` 只使用原 gold-like split 候选。",
            "- `expanded_manifest.json` 额外吸收 promotion 和 synthetic 候选，用于先跑更接近 benchmark 的训练与评估。",
            "- `expanded_override_rows.jsonl` 物化了 promotion 的 auto 标签和 synthetic 样本，供导 bundle 时叠加输入。",
            "",
            "## 当前摘要",
            "",
            "```json",
            json.dumps(summary, ensure_ascii=False, indent=2),
            "```",
            "",
            "## 使用边界",
            "",
            "- `gold_manifest.json` 适合先跑高置信度 pre-benchmark。",
            "- `expanded_manifest.json` 适合先跑 coverage 更完整的 pre-benchmark。",
            "- 如果要宣称正式 benchmark，仍需人工复核后重新冻结。",
            "",
        ]
    ) + "\n"


def write_freeze_pack(output_dir: Path, pack: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gold_manifest.json").write_text(json.dumps(pack["gold_manifest"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "expanded_manifest.json").write_text(json.dumps(pack["expanded_manifest"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(output_dir / "decision_log.jsonl", pack["decision_log"])
    _write_jsonl(output_dir / "expanded_override_rows.jsonl", pack["expanded_override_rows"])
    (output_dir / "summary.json").write_text(json.dumps(pack["summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text(_build_readme(pack["summary"]), encoding="utf-8")


def main() -> int:
    args = parse_args()
    pack = build_freeze_pack(args.backfill_dir)
    write_freeze_pack(args.output_dir, pack)
    print(json.dumps({"output_dir": str(args.output_dir), "summary": pack["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
