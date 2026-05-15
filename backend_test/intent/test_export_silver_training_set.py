from __future__ import annotations

import json
from pathlib import Path

from evaluation.intent.export_intent_training_set import export_training_rows


def _silver_row(*, row_id: str, batch: str) -> dict:
    return {
        "id": row_id,
        "batch": batch,
        "input": {"user_query": "你好", "history": []},
        "gold": {
            "evidence": {
                "classifier_mode": "rule_plus_model",
                "required_signals": ["chat"],
                "required_rule_ids": ["intent.chat.greeting"],
                "rule_expectations": {"intent.chat.greeting": True},
                "unsupported_signals": {
                    "file_write_request": False,
                    "file_delete_request": False,
                    "kb_admin_request": False,
                    "privileged_operation": False,
                    "unknown_external_action": False,
                },
                "dependency_signals": {
                    "none": True,
                    "history_reference": False,
                    "previous_answer": False,
                    "previous_retrieval": False,
                    "ambiguous": False,
                },
            },
            "resolved": {
                "main_intent": "chat",
                "modifiers": {
                    "follow_up": False,
                    "challenge": False,
                    "ask_source": False,
                    "ask_capability": False,
                    "needs_clarification": False,
                    "out_of_scope": False,
                    "soft_doubt": False,
                },
                "task": {"complexity": "simple", "shape": "none"},
                "context_dependency": "none",
            },
            "control": {"route": "chat", "mode": "normal"},
        },
        "label_tier": "silver",
        "label_source": "auto_uplift_rule_pipeline",
        "review_status": "draft",
        "source_query_id": row_id,
    }


def test_export_training_rows_marks_silver_rows_with_silver_label_tier(tmp_path: Path) -> None:
    silver_dir = tmp_path / "silver_dataset"
    silver_dir.mkdir()
    (silver_dir / "rows.json").write_text(
        json.dumps([_silver_row(row_id="silver_001", batch="chat")], ensure_ascii=False),
        encoding="utf-8",
    )

    exported = export_training_rows(train_dataset_dirs=[], dev_dataset_dirs=[], heldout_dataset_dirs=[], silver_dataset_dirs=[silver_dir])

    assert len(exported) == 1
    assert exported[0]["split"] == "train"
    assert exported[0]["metadata"]["label_tier"] == "silver"
    assert exported[0]["metadata"]["label_source"] == "auto_uplift_rule_pipeline"
    assert exported[0]["metadata"]["review_status"] == "draft"
