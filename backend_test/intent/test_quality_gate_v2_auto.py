from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.quality_gate_v2_auto import main, run_quality_gate


def _valid_row() -> dict:
    return {
        "id": "demo_001",
        "batch": "demo_batch",
        "legacy_gold": {
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
                    "complexity": "compound",
                    "shape": "multi_question",
                },
                "context_dependency": "none",
            }
        },
        "gold": {
            "evidence": {
                "signal_buckets": {
                    "intent": ["qa"],
                    "task": ["multi_question"],
                    "context": [],
                    "safety": [],
                }
            },
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
                    "complexity": "compound",
                    "shape": "multi_question",
                    "topology": "parallel_queries",
                },
                "context_dependency": "none",
            },
            "control": {"route": "rag", "mode": "normal"},
        },
    }


def test_run_quality_gate_passes_valid_rows_and_reports_drift_warning(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "demo.jsonl").write_text(json.dumps(_valid_row(), ensure_ascii=False) + "\n", encoding="utf-8")

    result = run_quality_gate(report_dir)

    assert result["rows"] == 1
    assert result["violation_count"] == 0
    assert result["warning_count"] >= 0


def test_run_quality_gate_flags_unknown_signal_and_inconsistent_task(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    row = _valid_row()
    row["gold"]["evidence"]["signal_buckets"]["intent"].append("unknown_signal")
    row["gold"]["resolved"]["task"]["complexity"] = "simple"
    row["gold"]["resolved"]["task"]["topology"] = "parallel_queries"
    (report_dir / "demo.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    result = run_quality_gate(report_dir)

    assert result["violation_count"] >= 2
    assert any(item["kind"] == "unknown_signal" for item in result["violations"])
    assert any(item["kind"] == "inconsistent_task" for item in result["violations"])


def test_run_quality_gate_flags_cross_bucket_signals_as_violation(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    row = _valid_row()
    row["gold"]["evidence"]["signal_buckets"]["intent"].append("ask_source")
    row["gold"]["evidence"]["signal_buckets"]["context"].append("ask_source")
    row["gold"]["resolved"]["modifiers"]["ask_source"] = True
    (report_dir / "demo.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    result = run_quality_gate(report_dir)

    assert result["violation_count"] >= 1
    assert any(item["kind"] == "unknown_signal" or item["kind"] == "cross_bucket_signal" for item in result["violations"])


def test_main_writes_gate_report_and_returns_nonzero_on_violation(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    row = _valid_row()
    row["gold"]["resolved"]["main_intent"] = "system"
    row["gold"]["resolved"]["modifiers"]["ask_capability"] = False
    row["gold"]["resolved"]["task"]["shape"] = "single_question"
    (report_dir / "demo.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    monkeypatch.setattr(
        "sys.argv",
        [
            "quality_gate_v2_auto.py",
            str(report_dir),
            str(output_dir),
        ],
    )

    exit_code = main()

    assert exit_code == 1
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "report.md").exists()
