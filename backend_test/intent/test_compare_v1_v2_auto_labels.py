from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.compare_v1_v2_auto_labels import build_diff_report, main


def _row() -> dict:
    return {
        "id": "demo_001",
        "batch": "demo_batch",
        "legacy_gold": {
            "evidence": {
                "required_signals": ["qa", "multi_question"],
                "dependency_signals": {
                    "none": False,
                    "history_reference": True,
                    "previous_answer": False,
                    "previous_retrieval": False,
                    "ambiguous": False,
                },
            },
            "resolved": {
                "main_intent": "qa",
                "modifiers": {
                    "follow_up": True,
                    "challenge": False,
                    "soft_doubt": False,
                    "ask_source": False,
                    "ask_capability": False,
                    "needs_clarification": False,
                    "out_of_scope": False,
                },
                "task": {
                    "complexity": "compound",
                    "shape": "multi_question",
                },
                "context_dependency": "history_reference",
            },
            "control": {
                "route": "rag",
                "mode": "normal",
            },
        },
        "gold": {
            "evidence": {
                "signal_buckets": {
                    "intent": ["qa"],
                    "task": ["parallel_subtasks"],
                    "context": ["follow_up"],
                    "safety": [],
                }
            },
            "resolved": {
                "main_intent": "qa",
                "modifiers": {
                    "follow_up": True,
                    "challenge": False,
                    "soft_doubt": False,
                    "ask_source": False,
                    "ask_capability": False,
                    "needs_clarification": False,
                    "out_of_scope": False,
                },
                "task": {
                    "complexity": "compound",
                    "shape": "multi_question",
                    "topology": "parallel_subtasks",
                },
                "context_dependency": "history_reference",
            },
            "control": {
                "route": "rag",
                "mode": "normal",
            },
        },
    }


def test_build_diff_report_counts_signal_and_topology_changes(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "demo.jsonl").write_text(json.dumps(_row(), ensure_ascii=False) + "\n", encoding="utf-8")

    report = build_diff_report(report_dir)

    assert report["overall"]["rows"] == 1
    assert report["overall"]["evidence_changed_rows"] == 1
    assert report["overall"]["signal_added_counts"]["parallel_subtasks"] == 1
    assert report["overall"]["signal_removed_counts"]["multi_question"] == 1
    assert report["overall"]["field_change_counts"]["resolved.task.topology"] == 1


def test_main_writes_summary_and_markdown_report(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "demo.jsonl").write_text(json.dumps(_row(), ensure_ascii=False) + "\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        "sys.argv",
        [
            "compare_v1_v2_auto_labels.py",
            str(report_dir),
            str(output_dir),
        ],
    )

    exit_code = main()

    assert exit_code == 0
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "report.md").exists()
