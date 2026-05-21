from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.intent.v2_sft.freeze_benchmark_candidates import build_freeze_pack, write_freeze_pack


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_build_freeze_pack_writes_gold_and_expanded_manifests(tmp_path: Path) -> None:
    backfill_dir = tmp_path / "benchmark_backfill"
    backfill_dir.mkdir()
    (backfill_dir / "split_manifest.json").write_text(
        json.dumps(
            {
                "version": "2026-05-19",
                "task": "v2_benchmark_backfill",
                "entries": [
                    {
                        "id": "gold_dev_001",
                        "split": "dev",
                        "status": "pending_review_gold",
                        "source_dataset": "seed_query_20260516_gold_v1",
                        "label_tier": "gold",
                        "reason": "dev_backfill_gold",
                    },
                    {
                        "id": "gold_held_001",
                        "split": "heldout",
                        "status": "legacy_seed",
                        "source_dataset": "frozen_heldout_v2",
                        "label_tier": "gold",
                        "reason": "retain_existing_heldout",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (backfill_dir / "summary.json").write_text(
        json.dumps(
            {
                "task": "v2_benchmark_backfill",
                "input_files": {
                    "topology_export": str(tmp_path / "topology.jsonl"),
                    "auto_export": str(tmp_path / "auto.jsonl"),
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "topology.jsonl",
        [
            {
                "id": "gold_dev_001",
                "split": "train",
                "input": {"user_query": "gold", "history": []},
                "evidence": {"context_signals": {}},
                "resolved": {
                    "main_intent": "qa",
                    "modifiers": {"follow_up": False, "challenge": False, "soft_doubt": False, "ask_source": False, "ask_capability": False, "needs_clarification": False, "out_of_scope": False},
                    "task": {"complexity": "simple", "shape": "single_question", "topology": "single"},
                },
                "metadata": {"source_dataset": "seed_query_20260516_gold_v1", "label_tier": "gold"},
            },
            {
                "id": "gold_held_001",
                "split": "heldout",
                "input": {"user_query": "held", "history": []},
                "evidence": {"context_signals": {}},
                "resolved": {
                    "main_intent": "qa",
                    "modifiers": {"follow_up": False, "challenge": False, "soft_doubt": False, "ask_source": False, "ask_capability": False, "needs_clarification": False, "out_of_scope": False},
                    "task": {"complexity": "simple", "shape": "single_question", "topology": "single"},
                },
                "metadata": {"source_dataset": "frozen_heldout_v2", "label_tier": "gold"},
            },
            {
                "id": "promo_001",
                "split": "train",
                "input": {"user_query": "promo", "history": []},
                "evidence": {"context_signals": {"clarify_hint": True, "ambiguous": True}},
                "resolved": {
                    "main_intent": "qa",
                    "modifiers": {"follow_up": False, "challenge": False, "soft_doubt": False, "ask_source": False, "ask_capability": False, "needs_clarification": True, "out_of_scope": False},
                    "task": {"complexity": "complex", "shape": "mixed", "topology": "staged"},
                },
                "metadata": {"source_dataset": "intent_query_full_set_campaign_v1_silver_v1", "label_tier": "silver"},
            },
        ],
    )
    _write_jsonl(tmp_path / "auto.jsonl", [json.loads(line) for line in (tmp_path / "topology.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()])
    _write_jsonl(
        backfill_dir / "review_candidates.jsonl",
        [
            {"id": "gold_dev_001", "queue": "eval_review"},
        ],
    )
    _write_jsonl(
        backfill_dir / "promotion_candidates.jsonl",
        [
            {
                "id": "promo_001",
                "proposed_split": "calibration",
                "source_dataset": "intent_query_full_set_campaign_v1_silver_v1",
                "label_tier": "silver",
                "gap_features": ["task_topology:staged"],
            }
        ],
    )
    _write_jsonl(
        backfill_dir / "synthetic_candidates.jsonl",
        [
                {
                    "id": "synthetic_001",
                    "proposed_split": "heldout",
                    "source_dataset": "synthetic_benchmark_backfill_20260519",
                    "label_tier": "synthetic",
                    "gap_features": ["task_topology:parallel_queries"],
                    "proposed_labels": {
                        "main_intent": "qa",
                        "task_complexity": "compound",
                        "task_shape": "multi_question",
                        "task_topology": "parallel_queries",
                        "modifiers": [],
                        "context": [],
                    },
                    "template_kind": "task_topology_parallel_queries",
                    "text": "请分别回答两个并列问题：一是接口越权风险怎么判断，二是日志保留策略通常要满足哪些要求。",
                }
            ],
        )

    pack = build_freeze_pack(backfill_dir)
    output_dir = tmp_path / "benchmark_ready"
    write_freeze_pack(output_dir, pack)

    gold_manifest = json.loads((output_dir / "gold_manifest.json").read_text(encoding="utf-8"))
    expanded_manifest = json.loads((output_dir / "expanded_manifest.json").read_text(encoding="utf-8"))
    decisions = [json.loads(line) for line in (output_dir / "decision_log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    override_rows = [json.loads(line) for line in (output_dir / "expanded_override_rows.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    assert gold_manifest["task"] == "v2_benchmark_auto_freeze_gold_only"
    assert expanded_manifest["task"] == "v2_benchmark_auto_freeze_expanded"
    assert len(gold_manifest["entries"]) == 2
    assert len(expanded_manifest["entries"]) == 4
    assert any(item["decision"] == "accept_auto_promotion" for item in decisions)
    assert any(item["decision"] == "accept_synthetic_gap_fill" for item in decisions)
    assert any(row["id"] == "promo_001" for row in override_rows)
    assert any(row["id"] == "synthetic_001" for row in override_rows)
