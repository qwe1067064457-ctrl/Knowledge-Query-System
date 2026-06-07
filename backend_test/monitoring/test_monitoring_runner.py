from __future__ import annotations

from monitoring.core.runner import run_monitoring


def test_run_monitoring_builds_layered_timeline_and_metrics() -> None:
    events = [
        {
            "event_type": "intent_classification_run",
            "trace_id": "trace-1",
            "status": "success",
            "latency_ms": 3,
            "started_at": "2026-06-04T10:00:00",
            "ended_at": "2026-06-04T10:00:00",
            "input_summary": {"query": "问题"},
            "output_summary": {"route": "qa"},
            "metadata": {"session_id": "s1"},
        },
        {
            "event_type": "context_assembly_run",
            "trace_id": "trace-1",
            "status": "success",
            "latency_ms": 5,
            "started_at": "2026-06-04T10:00:01",
            "ended_at": "2026-06-04T10:00:01",
            "input_summary": {"query": "问题"},
            "output_summary": {
                "memory_retrieval": {
                    "performed": True,
                    "owner": "context",
                    "source": "memory",
                }
            },
            "metadata": {"session_id": "s1"},
        },
        {
            "event_type": "workflow_run",
            "trace_id": "trace-1",
            "status": "success",
            "latency_ms": 7,
            "started_at": "2026-06-04T10:00:02",
            "ended_at": "2026-06-04T10:00:02",
            "input_summary": {"message": "问题"},
            "output_summary": {"status": "ready"},
            "metadata": {"workflow_name": "qa", "session_id": "s1"},
        },
        {
            "event_type": "answer_model_run",
            "trace_id": "trace-1",
            "status": "success",
            "latency_ms": 11,
            "started_at": "2026-06-04T10:00:03",
            "ended_at": "2026-06-04T10:00:03",
            "input_summary": {"messages_summary": {"message_count": 3}},
            "output_summary": {"payload_summary": {"action": "respond"}},
            "metadata": {"session_id": "s1"},
        },
    ]

    report = run_monitoring(events)

    assert report["timelines"][0]["stages"][0]["name"] == "intent"
    assert report["timelines"][0]["stages"][1]["name"] == "context"
    assert report["metrics"]["request_count"] == 1
    assert report["metrics"]["route_distribution"]["qa"] == 1
    assert report["metrics"]["action_distribution"]["respond"] == 1
    assert report["metrics"]["retrieval_run_rate"] == 1.0


def test_run_monitoring_handles_empty_events_without_failure() -> None:
    report = run_monitoring([])

    assert report["timelines"] == []
    assert report["metrics"]["request_count"] == 0
    assert report["failures"] == {}
