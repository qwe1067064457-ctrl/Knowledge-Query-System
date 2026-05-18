from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.export_v2_auto_training_set import export_v2_auto_training_rows, main


def test_export_v2_auto_training_rows_converts_auto_annotation_report_to_training_rows(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    row = {
        "id": "demo_001",
        "batch": "demo_batch",
        "input": {"user_query": "测试问题", "history": []},
        "gold": {
            "evidence": {"classifier_mode": "rule_plus_model"},
            "resolved": {
                "main_intent": "qa",
                "modifiers": {
                    "follow_up": False,
                    "challenge": False,
                    "soft_doubt": False,
                    "ask_source": True,
                    "ask_capability": False,
                    "needs_clarification": False,
                    "out_of_scope": False,
                },
                "task": {
                    "complexity": "simple",
                    "shape": "single_question",
                    "topology": "single",
                },
                "context_dependency": "previous_answer",
            },
            "control": {
                "route": "rag",
                "mode": "normal",
                "rewrite": True,
                "force_citation": True,
                "use_planner": False,
                "decompose_query": False,
                "planning_level": "none",
            },
        },
        "legacy_gold": {
            "evidence": {
                "rule_expectations": {"source.ask_basis": True},
            }
        },
        "source_query_id": "source_001",
        "label_source": "v2_auto_annotator",
        "review_status": "draft",
        "migration_review": {
            "required": True,
            "reasons": ["modifier_ask_source"],
        },
        "label_tier": "gold",
    }
    (report_dir / "seed_query_20260514_gold_v1.jsonl").write_text(
        json.dumps(row, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    exported = export_v2_auto_training_rows(report_dir)

    assert len(exported) == 1
    assert exported[0]["split"] == "train"
    assert exported[0]["resolved"]["task"]["topology"] == "single"
    assert exported[0]["metadata"]["schema_version"] == "v2_auto"
    assert exported[0]["metadata"]["is_auto_relabeled"] is True
    assert exported[0]["metadata"]["review_required"] is True
    assert exported[0]["metadata"]["is_strict_rule_supervision"] is True


def test_main_writes_v2_auto_training_jsonl(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    row = {
        "id": "demo_001",
        "batch": "demo_batch",
        "input": {"user_query": "测试问题", "history": []},
        "gold": {
            "evidence": {"classifier_mode": "rule_plus_model"},
            "resolved": {
                "main_intent": "qa",
                "modifiers": {
                    "follow_up": False,
                    "challenge": False,
                    "soft_doubt": False,
                    "ask_source": False,
                    "ask_capability": False,
                    "needs_clarification": False,
                    "out_of_scope": False,
                },
                "task": {
                    "complexity": "simple",
                    "shape": "single_question",
                    "topology": "single",
                },
                "context_dependency": "none",
            },
            "control": {"route": "rag", "mode": "normal"},
        },
        "legacy_gold": {"evidence": {"rule_expectations": {}}},
    }
    (report_dir / "seed_query_20260514_gold_v1.jsonl").write_text(
        json.dumps(row, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "intent_training_v2_auto.jsonl"
    monkeypatch.setattr(
        "sys.argv",
        [
            "export_v2_auto_training_set.py",
            str(report_dir),
            str(output_path),
        ],
    )

    exit_code = main()

    assert exit_code == 0
    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["metadata"]["schema_version"] == "v2_auto"
