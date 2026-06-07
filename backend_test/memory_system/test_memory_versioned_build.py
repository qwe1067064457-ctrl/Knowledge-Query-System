from __future__ import annotations

import json
from datetime import date

import pytest

from helpers import make_memory_system, temp_workspace


def test_memory_search_builds_versioned_current_latest_and_snapshot() -> None:
    with temp_workspace() as workspace:
        memory = make_memory_system(workspace)
        memory.write_daily_log(
            "law",
            "default",
            "今天继续讨论 breach liability 与 damages。",
            target_date=date(2026, 6, 2),
            user_id="u1",
            title="Daily checkpoint",
        )
        memory.write_domain_case(
            group_id="law",
            user_id="u1",
            title="Breach liability case",
            content="The case emphasizes foreseeability in breach liability.",
        )

        results = memory.search("law", "default", "breach liability foreseeability", user_id="u1", min_score=0.01, top_k=5)

        memory_root = workspace / "storage" / "groups" / "law" / "users" / "u1" / "indexes" / "memory"
        manifest = json.loads((memory_root / "registries" / "index_manifest.json").read_text(encoding="utf-8"))
        build_id = manifest["current_build_id"]
        snapshot_id = manifest["current_snapshot_id"]

        assert results
        assert (memory_root / "current" / "chunk_store.sqlite").exists()
        assert (memory_root / "builds" / "running" / build_id / "chunk_store.sqlite").exists()
        assert (memory_root / "builds" / "latest" / build_id / "chunk_store.sqlite").exists()
        assert (memory_root / "snapshots" / snapshot_id / "chunk_store.sqlite").exists()
        assert (memory_root / "registries" / "recovery" / "entry_checkpoints.sqlite").exists()
        assert (memory_root / "registries" / "history" / "build_history.jsonl").exists()


def test_memory_search_skips_rebuild_when_fingerprint_unchanged() -> None:
    with temp_workspace() as workspace:
        memory = make_memory_system(workspace)
        memory.write_daily_log(
            "law",
            "default",
            "今天继续讨论 breach liability。",
            target_date=date(2026, 6, 2),
            user_id="u1",
        )

        first = memory.search("law", "default", "breach liability", user_id="u1", min_score=0.01, top_k=5)
        history_path = workspace / "storage" / "groups" / "law" / "users" / "u1" / "indexes" / "memory" / "registries" / "history" / "build_registry.jsonl"
        rows_after_first = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        second = memory.search("law", "default", "breach liability", user_id="u1", min_score=0.01, top_k=5)
        rows_after_second = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]

        assert first
        assert second
        assert [row["status"] for row in rows_after_first] == ["running", "validated", "activated"]
        assert rows_after_second == rows_after_first


def test_memory_search_falls_back_to_old_current_when_new_build_fails() -> None:
    with temp_workspace() as workspace:
        memory = make_memory_system(workspace)
        memory.write_domain_case(
            group_id="law",
            user_id="u1",
            title="Breach liability case",
            content="The case emphasizes foreseeability in breach liability.",
        )
        baseline = memory.search(
            "law",
            "default",
            "breach liability foreseeability",
            user_id="u1",
            include_core=False,
            include_daily_logs=False,
            min_score=0.01,
            top_k=5,
        )
        memory.write_daily_log(
            "law",
            "default",
            "这条新日志会触发新的构建。",
            target_date=date(2026, 6, 3),
            user_id="u1",
        )

        class EmptyChunker:
            def chunk(self, document):
                return ()

        memory.index_manager.chunker = EmptyChunker()
        fallback = memory.search(
            "law",
            "default",
            "breach liability foreseeability",
            user_id="u1",
            include_core=False,
            include_daily_logs=False,
            min_score=0.01,
            top_k=5,
        )

        validation_path = workspace / "storage" / "groups" / "law" / "users" / "u1" / "indexes" / "memory" / "registries" / "history" / "validation_history.jsonl"
        validations = [json.loads(line) for line in validation_path.read_text(encoding="utf-8").splitlines() if line.strip()]

        assert baseline
        assert fallback
        assert fallback[0].title == baseline[0].title
        assert validations[-1]["status"] == "failed"
        assert any("entry failed during build" in item or "entry missing chunk output" in item for item in validations[-1]["blocking_errors"])
