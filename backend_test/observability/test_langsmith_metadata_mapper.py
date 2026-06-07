from __future__ import annotations

from observability.contracts.events import ObservabilityEvent
from observability.langsmith.metadata_mapper import map_event_to_langsmith_payload


def test_metadata_mapper_projects_context_event_to_stable_langsmith_shape() -> None:
    event = ObservabilityEvent(
        event_type="context_assembly_run",
        run_id="run_1",
        parent_run_id=None,
        trace_id="trace_1",
        status="success",
        started_at="2026-06-03T10:00:00",
        ended_at="2026-06-03T10:00:01",
        latency_ms=1000,
        input_summary={"query": "breach damages"},
        output_summary={"needs_compaction": False},
        metadata={"session_id": "s1", "workflow_name": "qa"},
    )

    payload = map_event_to_langsmith_payload(event)

    assert payload["name"] == "context.assembly"
    assert payload["run_type"] == "chain"
    assert payload["inputs"] == {"query": "breach damages"}
    assert payload["outputs"] == {"needs_compaction": False}
    assert "event:context_assembly_run" in payload["tags"]
    assert "workflow:qa" in payload["tags"]


def test_metadata_mapper_handles_sparse_event_fields() -> None:
    event = ObservabilityEvent(
        event_type="retrieval_run",
        run_id="run_2",
        parent_run_id=None,
        trace_id="trace_2",
        status="success",
        started_at="2026-06-03T10:00:00",
        ended_at="2026-06-03T10:00:00",
        latency_ms=0,
    )

    payload = map_event_to_langsmith_payload(event)

    assert payload["name"] == "retrieval.run"
    assert payload["inputs"] == {}
    assert payload["outputs"] == {}
    assert payload["metadata"]["trace_id"] == "trace_2"
