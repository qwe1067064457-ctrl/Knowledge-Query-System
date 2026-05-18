from __future__ import annotations

from evaluation.intent.v2_migration import serialize_evidence_v2, serialize_resolved_v2


def test_serialize_resolved_v2_infers_parallel_query_topology_from_v1_compound() -> None:
    resolved = {
        "main_intent": "qa",
        "modifiers": {},
        "task": {
            "complexity": "compound",
            "shape": "multi_question",
        },
        "context_dependency": "none",
    }

    serialized = serialize_resolved_v2(resolved)

    assert serialized["task"]["complexity"] == "compound"
    assert serialized["task"]["shape"] == "multi_question"
    assert serialized["task"]["topology"] == "parallel_queries"


def test_serialize_resolved_v2_keeps_single_topology_for_simple_queries() -> None:
    resolved = {
        "main_intent": "qa",
        "modifiers": {},
        "task": {
            "complexity": "simple",
            "shape": "single_question",
        },
        "context_dependency": "none",
    }

    serialized = serialize_resolved_v2(resolved)

    assert serialized["task"]["topology"] == "single"


def test_serialize_resolved_v2_adds_ambiguity_state_from_legacy_clarify_signal() -> None:
    resolved = {
        "main_intent": "qa",
        "modifiers": {
            "needs_clarification": True,
        },
        "task": {
            "complexity": "simple",
            "shape": "single_question",
        },
        "context_dependency": "ambiguous",
    }

    serialized = serialize_resolved_v2(resolved)

    assert serialized["ambiguity_state"]["clarify_candidate"] is True
    assert serialized["ambiguity_state"]["needs_context_check"] is True
    assert serialized["ambiguity_state"]["possibly_ambiguous"] is True


def test_serialize_evidence_v2_prefers_context_signals_over_dependency_signals() -> None:
    evidence = {
        "classifier_mode": "rule_plus_model",
        "required_signals": ["qa"],
        "required_rule_ids": [],
        "rule_expectations": {},
        "unsupported_signals": {},
        "dependency_signals": {"none": False, "history_reference": True, "previous_answer": False, "previous_retrieval": False, "ambiguous": False},
        "context_signals": {
            "none": False,
            "history_reference": False,
            "needs_previous_answer": True,
            "previous_answer": True,
            "previous_retrieval": False,
            "missing_reference_target": False,
            "possibly_ambiguous": False,
            "needs_context_check": False,
            "ambiguous": False,
        },
    }

    serialized = serialize_evidence_v2(evidence)

    assert serialized["context_signals"]["previous_answer"] is True
    assert serialized["context_signals"]["needs_previous_answer"] is True
    assert "dependency_signals" not in serialized


def test_serialize_evidence_v2_infers_context_signals_when_missing() -> None:
    evidence = {
        "classifier_mode": "rule_plus_model",
        "required_signals": ["qa"],
        "required_rule_ids": [],
        "rule_expectations": {},
        "unsupported_signals": {},
        "dependency_signals": {"none": False, "history_reference": True, "previous_answer": False, "previous_retrieval": False, "ambiguous": False},
    }

    serialized = serialize_evidence_v2(evidence)

    assert serialized["context_signals"]["history_reference"] is True
    assert serialized["signal_buckets"]["context_fact"] == ["history_reference"]
