from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evaluation.intent.evaluate_intent_rules import evaluate_dataset, load_dataset


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "adversarial-intent-test-generator" / "scripts" / "scaffold_intent_dataset.py"


def test_skill_generator_creates_prefilled_campaign(tmp_path: Path) -> None:
    output_dir = tmp_path / "campaign"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(output_dir),
            "--profile",
            "v1_adversarial_campaign",
        ],
        check=True,
        cwd=ROOT,
    )

    follow_up_path = output_dir / "follow_up.json"
    challenge_path = output_dir / "challenge.json"
    readme_path = output_dir / "README.md"

    assert follow_up_path.exists()
    assert challenge_path.exists()
    assert readme_path.exists()

    follow_up_rows = json.loads(follow_up_path.read_text(encoding="utf-8"))
    challenge_rows = json.loads(challenge_path.read_text(encoding="utf-8"))

    assert len(follow_up_rows) == 25
    assert len(challenge_rows) == 25
    assert follow_up_rows[0]["gold"]["resolved"]["modifiers"]["follow_up"] is True
    assert challenge_rows[0]["gold"]["resolved"]["modifiers"]["challenge"] is True
    assert "review_hints" in follow_up_rows[0]
    assert "consistency_checks" in follow_up_rows[0]["review_hints"]


def test_skill_generator_campaign_exposes_nontrivial_eval(tmp_path: Path) -> None:
    output_dir = tmp_path / "campaign"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(output_dir),
            "--profile",
            "v1_adversarial_campaign",
        ],
        check=True,
        cwd=ROOT,
    )

    rows = load_dataset(output_dir)
    summary = evaluate_dataset(rows)

    assert summary["overall"]["samples"] == 50
    assert summary["overall"]["resolved_main_intent_accuracy"] < 1.0
    assert summary["overall"]["control_route_accuracy"] < 1.0


def test_skill_generator_can_build_twins_campaign_v2(tmp_path: Path) -> None:
    output_dir = tmp_path / "twins_campaign_v2"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(output_dir),
            "--profile",
            "twins_campaign_v2",
        ],
        check=True,
        cwd=ROOT,
    )

    challenge_rows = json.loads((output_dir / "challenge_twins.json").read_text(encoding="utf-8"))
    follow_up_rows = json.loads((output_dir / "follow_up_twins.json").read_text(encoding="utf-8"))
    qa_system_rows = json.loads((output_dir / "qa_system_twins.json").read_text(encoding="utf-8"))

    assert len(challenge_rows) == 8
    assert len(follow_up_rows) == 8
    assert len(qa_system_rows) == 8
    assert any("HISTORY_SUPPORT_UNCLEAR" in row["review_hints"]["risk_flags"] for row in challenge_rows)
    assert any(row["gold"]["resolved"]["main_intent"] == "system" for row in qa_system_rows)

    summary = evaluate_dataset(load_dataset(output_dir))
    assert summary["overall"]["samples"] == 24
    assert summary["overall"]["resolved_main_intent_accuracy"] < 1.0
    assert summary["overall"]["control_route_accuracy"] < 1.0


def test_skill_generator_can_build_campaign_from_txt_query_list(tmp_path: Path) -> None:
    input_file = tmp_path / "queries.txt"
    input_file.write_text(
        "那这种情况呢？\n你确定吗？\n这个依据是什么？\n这样算不算医疗事故？\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "query_campaign"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(output_dir),
            "--profile",
            "from_query_list",
            "--input-file",
            str(input_file),
            "--sample-limit",
            "4",
        ],
        check=True,
        cwd=ROOT,
    )

    rows = load_dataset(output_dir)

    assert len(rows) >= 6
    assert any(row["source_query_id"] == "query_001" for row in rows)
    assert any("risk_flags" in row["review_hints"] for row in rows)
    assert any("CONTROL_ROUTE_COST_RISK" in row["review_hints"]["risk_flags"] for row in rows)


def test_skill_generator_accepts_jsonl_query_list_with_hints(tmp_path: Path) -> None:
    input_file = tmp_path / "queries.jsonl"
    input_file.write_text(
        "\n".join(
            [
                json.dumps({"id": "a1", "query": "那如果没有证据呢？", "hints": {"preferred_batch": "follow_up"}}, ensure_ascii=False),
                json.dumps({"id": "a2", "query": "你刚才这个说法不对吧？", "hints": {"preferred_batch": "challenge"}}, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "query_campaign_jsonl"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(output_dir),
            "--profile",
            "from_query_list",
            "--input-file",
            str(input_file),
            "--generation-modes",
            "near_miss",
            "cost_focused",
        ],
        check=True,
        cwd=ROOT,
    )

    rows = load_dataset(output_dir)

    assert any(row["source_query_id"] == "a1" for row in rows)
    assert any(row["source_query_id"] == "a2" for row in rows)
    assert any(row["review_hints"]["generation_mode"] == "near_miss" for row in rows)
