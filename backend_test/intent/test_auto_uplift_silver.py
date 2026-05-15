from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.intent.auto_uplift_silver import auto_uplift_campaign_dataset


def _campaign_row(*, row_id: str, batch: str, query: str, history: list[dict] | None = None) -> dict:
    return {
        "id": row_id,
        "batch": batch,
        "input": {
            "user_query": query,
            "history": history or [],
        },
        "source_query_id": f"source::{row_id}",
        "notes": "campaign draft",
    }


def test_auto_uplift_campaign_dataset_writes_structured_silver_rows(tmp_path: Path) -> None:
    source_dir = tmp_path / "campaign_source"
    output_dir = tmp_path / "silver_output"
    source_dir.mkdir()
    rows = [
        _campaign_row(row_id="row_001", batch="chat", query="你好"),
        _campaign_row(
            row_id="row_002",
            batch="follow_up",
            query="那这种情况呢？",
            history=[
                {"role": "assistant", "content": "刚才我们先按合同责任做了拆解。"},
            ],
        ),
    ]
    (source_dir / "rows.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    summary = auto_uplift_campaign_dataset(source_dir=source_dir, output_dir=output_dir)

    assert summary["rows"] == 2
    assert summary["batches"] == 2
    assert summary["skipped_corrupted"] == 0
    assert (output_dir / "README.md").exists()

    chat_rows = json.loads((output_dir / "chat.json").read_text(encoding="utf-8"))
    follow_rows = json.loads((output_dir / "follow_up.json").read_text(encoding="utf-8"))

    assert chat_rows[0]["label_tier"] == "silver"
    assert chat_rows[0]["label_source"] == "auto_uplift_rule_pipeline"
    assert chat_rows[0]["review_status"] == "draft"
    assert chat_rows[0]["gold"]["resolved"]["main_intent"] == "chat"
    assert chat_rows[0]["gold"]["control"]["route"] == "chat"

    assert follow_rows[0]["gold"]["resolved"]["modifiers"]["follow_up"] is True
    assert follow_rows[0]["gold"]["resolved"]["context_dependency"] == "history_reference"


def test_auto_uplift_campaign_dataset_rejects_rows_without_query(tmp_path: Path) -> None:
    source_dir = tmp_path / "campaign_source"
    output_dir = tmp_path / "silver_output"
    source_dir.mkdir()
    bad_rows = [
        {
            "id": "bad_001",
            "batch": "chat",
            "input": {"history": []},
        }
    ]
    (source_dir / "rows.json").write_text(json.dumps(bad_rows, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="user_query"):
        auto_uplift_campaign_dataset(source_dir=source_dir, output_dir=output_dir)


def test_auto_uplift_campaign_dataset_skips_question_mark_only_queries(tmp_path: Path) -> None:
    source_dir = tmp_path / "campaign_source"
    output_dir = tmp_path / "silver_output"
    source_dir.mkdir()
    rows = [
        _campaign_row(row_id="ok_001", batch="chat", query="你好"),
        _campaign_row(row_id="bad_002", batch="chat", query="????????"),
    ]
    (source_dir / "rows.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    summary = auto_uplift_campaign_dataset(source_dir=source_dir, output_dir=output_dir)

    exported = json.loads((output_dir / "chat.json").read_text(encoding="utf-8"))
    assert summary["rows"] == 1
    assert summary["skipped_corrupted"] == 1
    assert [row["id"] for row in exported] == ["ok_001"]
