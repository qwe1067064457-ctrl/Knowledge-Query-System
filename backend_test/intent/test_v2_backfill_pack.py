from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.intent.v2_sft.build_backfill_pack import build_backfill_pack, write_backfill_pack


def _make_row(
    *,
    row_id: str,
    split: str,
    tier: str,
    source_dataset: str,
    main_intent: str,
    task_complexity: str,
    task_shape: str,
    task_topology: str,
    modifiers: dict[str, bool] | None = None,
    context_signals: dict[str, bool] | None = None,
) -> dict:
    return {
        "id": row_id,
        "split": split,
        "input": {"user_query": f"query:{row_id}", "history": []},
        "evidence": {
            "context_signals": {
                "history_reference": bool((context_signals or {}).get("history_reference", False)),
                "previous_answer": bool((context_signals or {}).get("needs_previous_answer", False)),
                "previous_retrieval": bool((context_signals or {}).get("previous_retrieval", False)),
                "clarify_hint": bool((context_signals or {}).get("clarify_hint", False)),
                "ambiguous": bool((context_signals or {}).get("clarify_hint", False)),
            }
        },
        "resolved": {
            "main_intent": main_intent,
            "modifiers": {
                "follow_up": False,
                "challenge": False,
                "soft_doubt": False,
                "ask_source": False,
                "ask_capability": False,
                "needs_clarification": False,
                "out_of_scope": False,
                **(modifiers or {}),
            },
            "task": {
                "complexity": task_complexity,
                "shape": task_shape,
                "topology": task_topology,
            },
        },
        "metadata": {
            "source_dataset": source_dataset,
            "label_tier": tier,
        },
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_build_backfill_pack_generates_manifest_and_review_queues(tmp_path: Path) -> None:
    topology_rows = [
        _make_row(
            row_id="dev_seed",
            split="dev",
            tier="gold",
            source_dataset="seed_query_20260516_gold_v1",
            main_intent="qa",
            task_complexity="simple",
            task_shape="verify",
            task_topology="single",
            modifiers={"challenge": True},
            context_signals={"needs_previous_answer": True},
        ),
        _make_row(
            row_id="held_seed",
            split="heldout",
            tier="gold",
            source_dataset="seed_query_20260514_gold_v1",
            main_intent="unsupported",
            task_complexity="complex",
            task_shape="compare",
            task_topology="parallel_queries",
            modifiers={"out_of_scope": True},
        ),
    ]
    for index in range(90):
        topology_rows.append(
            _make_row(
                row_id=f"gold_train_{index:03d}",
                split="train",
                tier="gold",
                source_dataset="seed_query_20260517_gold_v1" if index % 2 else "seed_query_20260516_gold_v1",
                main_intent="chat" if index % 7 == 0 else ("system" if index % 11 == 0 else "qa"),
                task_complexity="complex" if index % 5 == 0 else ("compound" if index % 9 == 0 else "simple"),
                task_shape="multi_question" if index % 6 == 0 else ("verify" if index % 4 == 0 else "single_question"),
                task_topology="parallel_queries" if index % 8 == 0 else "single",
                modifiers={"follow_up": index % 3 == 0, "ask_source": index % 10 == 0, "soft_doubt": index % 12 == 0},
                context_signals={"needs_previous_answer": index % 4 == 0, "clarify_hint": index % 13 == 0},
            )
        )
    for index in range(10):
        topology_rows.append(
            _make_row(
                row_id=f"silver_train_{index:03d}",
                split="train",
                tier="silver",
                source_dataset="intent_query_full_set_campaign_v1_silver_v1",
                main_intent="qa",
                task_complexity="simple",
                task_shape="single_question",
                task_topology="single",
            )
        )

    auto_rows = []
    for row in topology_rows:
        auto_row = json.loads(json.dumps(row))
        if row["id"].startswith("gold_train_") and int(row["id"].split("_")[-1]) % 6 == 0:
            auto_row["resolved"]["task"]["shape"] = "compare"
        if row["id"].startswith("silver_train_") and int(row["id"].split("_")[-1]) % 2 == 0:
            auto_row["resolved"]["task"]["topology"] = "staged"
        auto_rows.append(auto_row)

    topology_path = tmp_path / "topology.jsonl"
    auto_path = tmp_path / "auto.jsonl"
    _write_jsonl(topology_path, topology_rows)
    _write_jsonl(auto_path, auto_rows)

    pack = build_backfill_pack(topology_path, auto_path)
    output_dir = tmp_path / "backfill"
    write_backfill_pack(output_dir, pack)

    manifest = json.loads((output_dir / "split_manifest.json").read_text(encoding="utf-8"))
    review_rows = [json.loads(line) for line in (output_dir / "review_candidates.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    weak_train_rows = [json.loads(line) for line in (output_dir / "weak_train_candidates.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    assert manifest["task"] == "v2_sample_backfill"
    assert any(entry["split"] == "calibration" for entry in manifest["entries"])
    assert any(row["queue"] == "eval_review" for row in review_rows)
    assert any(row["queue"] == "weak_train" for row in weak_train_rows)


def test_build_benchmark_backfill_pack_generates_promotion_candidates(tmp_path: Path) -> None:
    topology_rows = []
    for index in range(120):
        topology_rows.append(
            _make_row(
                row_id=f"gold_train_{index:03d}",
                split="train",
                tier="gold",
                source_dataset="seed_query_20260516_gold_v1",
                main_intent="qa" if index % 9 else "chat",
                task_complexity="complex" if index % 7 == 0 else ("compound" if index % 13 == 0 else "simple"),
                task_shape="verify" if index % 3 == 0 else ("multi_question" if index % 5 == 0 else "single_question"),
                task_topology="parallel_queries" if index % 8 == 0 else "single",
                modifiers={"follow_up": index % 4 == 0, "soft_doubt": index % 10 == 0, "ask_source": index % 12 == 0},
                context_signals={"needs_previous_answer": index % 6 == 0, "clarify_hint": index % 17 == 0},
            )
        )
    for index in range(20):
        topology_rows.append(
            _make_row(
                row_id=f"silver_train_{index:03d}",
                split="train",
                tier="silver",
                source_dataset="intent_query_full_set_campaign_v1_silver_v1",
                main_intent="qa",
                task_complexity="simple",
                task_shape="single_question",
                task_topology="single",
            )
        )

    auto_rows = []
    for row in topology_rows:
        auto_row = json.loads(json.dumps(row))
        if row["id"].startswith("silver_train_"):
            number = int(row["id"].split("_")[-1])
            if number % 2 == 0:
                auto_row["resolved"]["task"]["topology"] = "staged"
            else:
                auto_row["resolved"]["task"]["topology"] = "parallel_subtasks"
            auto_row["resolved"]["task"]["complexity"] = "complex"
            auto_row["resolved"]["modifiers"]["needs_clarification"] = True
            auto_row["evidence"]["context_signals"]["clarify_hint"] = True
        auto_rows.append(auto_row)

    topology_path = tmp_path / "topology.jsonl"
    auto_path = tmp_path / "auto.jsonl"
    _write_jsonl(topology_path, topology_rows)
    _write_jsonl(auto_path, auto_rows)

    pack = build_backfill_pack(topology_path, auto_path, profile="benchmark")
    output_dir = tmp_path / "benchmark_backfill"
    write_backfill_pack(output_dir, pack)

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    promotion_rows = [json.loads(line) for line in (output_dir / "promotion_candidates.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    synthetic_rows = [json.loads(line) for line in (output_dir / "synthetic_candidates.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    assert summary["task"] == "v2_benchmark_backfill"
    assert summary["promotion_queue"] > 0
    assert summary["synthetic_queue"] > 0
    assert any("task_topology:staged" in row["gap_features"] or "task_topology:parallel_subtasks" in row["gap_features"] for row in promotion_rows)
    assert any(row["status"] == "pending_review_synthetic" for row in synthetic_rows)
