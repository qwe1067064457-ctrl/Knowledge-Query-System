from __future__ import annotations

from pathlib import Path

from context.assembly.context_manager import ContextManager
from context.session.session_manager import SessionManager
from graph.agent import AgentManager
from graph.prompt_builders.workflow_prompt_projector import build_answer_result_projection_rules_from_workflow
from workflow.adapters.workflow_registry_projection import (
    build_execution_summary_metadata,
    build_registry_entries_from_execution_payload,
    build_registry_metadata_payload,
)
from memory_system import MemorySystem
from workflow.types import (
    ContextBindingResult,
    ContextBundle,
    EvidenceAssessmentResult,
    EvidenceBundle,
    EvidenceItem,
    ExecutionPayload,
    PlanBundle,
    ReviewBundle,
)


def test_execution_payload_is_persisted_into_registry(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    raw_session_manager = SessionManager(storage_root)
    memory_system = MemorySystem(storage_root)
    context_manager = ContextManager(raw_session_manager, memory_system)

    session = raw_session_manager.create_session(
        "general",
        "default",
        "tenant_u1",
        metadata={"active_group_id": "law", "allowed_group_ids": ["law"]},
    )

    agent = AgentManager()
    agent.raw_session_manager = raw_session_manager
    agent.context_manager = context_manager

    payload = ExecutionPayload(
        route="qa",
        handling_mode="normal",
        action="knowledge_orchestrator",
        context_bundle={},
        plan_bundle={
            "query_units": [{"unit_id": "q1", "origin": "primary", "text": "试用期依据是什么"}],
        },
        evidence_bundle=EvidenceBundle(
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="e1",
                    source_path="docs/law.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="劳动合同法第19条。",
                    channel="fused",
                    score=0.9,
                    query_unit_ids=("primary",),
                ),
            ),
            source_refs=("docs/law.md",),
        ),
    )

    agent._persist_execution_payload(
        payload=payload,
        session_id=session.id,
        group_id="law",
        message="试用期依据是什么",
    )

    registry = context_manager.load_registry(
        tenant_id="tenant_u1",
        group_id="law",
        agent_id="default",
        session_id=session.id,
    )

    assert len(registry.entries) == 3
    assert registry.entries[0].object_type == "question_object"
    assert registry.entries[0].metadata["binding_summary"] == "not_applicable"
    assert registry.entries[0].metadata["knowledge_scope_status"] == "resolved"
    assert registry.entries[0].metadata["evidence_summary"]["merged_evidence_count"] == 1
    assert registry.entries[0].metadata["workflow_summary"]["knowledge_scope_status"] == "resolved"
    assert registry.entries[0].metadata["registry_convenience"]["route"] == "qa"
    assert registry.entries[1].object_type == "evidence_ref"
    assert registry.entries[1].metadata["channel"] == "fused"
    assert registry.entries[1].metadata["evidence_summary"]["source_ref_count"] == 1
    assert registry.entries[1].metadata["review_summary"]["status_summary"] == "not_applicable"
    assert registry.entries[1].metadata["workflow_summary"]["evidence_summary"]["source_ref_count"] == 1
    assert registry.entries[1].metadata["registry_convenience"]["channel"] == "fused"
    assert registry.entries[2].object_type == "question_object"
    assert registry.entries[2].metadata["registry_convenience"]["unit_id"] == "q1"


def test_agent_builds_summary_driven_instructions() -> None:
    agent = AgentManager()
    payload = ExecutionPayload(
        route="qa",
        handling_mode="challenge",
        action="agent",
        key_events=("follow_up_retrieval_attempted", "insufficient_evidence"),
        context_bundle={
            "binding_summary": "bound_by_explicit_pattern",
            "candidate_count": 3,
            "query_units": [{"unit_id": "q1"}],
        },
        plan_bundle={
            "plan_summary": {
                "planning_mode": "compare",
                "step_count": 3,
                "checkpoint_count": 2,
                "comparison_unit_count": 1,
                "bound_target_ref_count": 2,
                "refined": False,
                "fallback_used": True,
                "fallback_reason": ["missing_compare_coverage"],
            }
        },
        review_bundle={
            "review_mode": "challenge_review",
            "review_confidence": "medium",
            "review_scope": "multi_target",
            "review_summary": {
                "status_summary": "partial_success",
                "target_count": 2,
                "matched_target_count": 1,
                "needs_more_evidence_targets": ["claim_2"],
                "follow_up_retrieval_attempted": True,
                "follow_up_retrieval_improved": False,
            },
        },
        evidence_bundle=EvidenceBundle(
            quality_summary={"average_weighted_score": 0.4, "status": "bad", "repaired_units": 1},
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="e1",
                    source_path="docs/law.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="劳动合同法第19条。",
                    channel="fused",
                    score=0.9,
                    query_unit_ids=("primary",),
                ),
            ),
            source_refs=("docs/law.md",),
            missing_evidence_notes=("retrieval_quality_weak",),
        ),
    )

    instructions = build_answer_result_projection_rules_from_workflow(payload)

    assert any("binding summary" in item for item in instructions)
    assert any("review summary" in item for item in instructions)
    assert any("evidence quality is bad" in item for item in instructions)
    assert any("still 1 target(s) needing more evidence" in item for item in instructions)
    assert any("follow-up retrieval was attempted" in item for item in instructions)
    assert any("Evidence remains insufficient" in item for item in instructions)
    assert any("evidence bundle is still incomplete" in item for item in instructions)
    assert not any("planning summary" in item for item in instructions)


def test_agent_builds_execution_summary_metadata_from_typed_summary_views() -> None:
    agent = AgentManager()
    payload = ExecutionPayload(
        route="qa",
        handling_mode="challenge",
        action="respond",
        context_bundle={
            "binding_summary": "bound_by_topic_continuity",
            "candidate_count": 2,
        },
        plan_bundle={
            "planning_mode": "compare",
            "ordered_steps": [{"title": "Compare", "sequence": 1}],
            "execution_checkpoints": [{"name": "coverage"}],
            "comparison_units": [{"left": "A", "right": "B"}],
            "bound_target_refs": ["compare_1"],
            "fallback_used": True,
            "fallback_reason": ["stale_plan_summary_should_not_win"],
            "plan_summary": {
                "planning_mode": "stale",
                "step_count": 99,
                "fallback_used": False,
            },
        },
        review_bundle={
            "review_mode": "challenge_review",
            "review_confidence": "medium",
            "review_scope": "multi_target",
            "evidence_assessment": EvidenceAssessmentResult(
                partially_sufficient=True,
                matched_target_count=1,
                target_count=2,
                matched_target_refs=("claim_1",),
                needs_more_evidence_targets=("claim_2",),
                follow_up_retrieval={
                    "attempted": True,
                    "improved": False,
                    "source_refs": ["kb/law.md"],
                    "retrieved_evidence_count": 1,
                },
            ),
            "review_summary": {
                "matched_target_count": 99,
                "needs_more_evidence_targets": ["stale_claim"],
                "follow_up_retrieval_attempted": False,
            },
        },
        evidence_bundle=EvidenceBundle(
            quality_summary={"average_weighted_score": 0.4, "status": "bad", "repaired_units": 1},
            coverage_summary={"query_units": 2, "sources": 1},
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="e1",
                    source_path="docs/law.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="劳动合同法第19条。",
                    channel="fused",
                    score=0.9,
                    query_unit_ids=("primary",),
                ),
            ),
            source_refs=("docs/law.md",),
            missing_evidence_notes=("retrieval_quality_weak",),
        ),
    )

    metadata = build_execution_summary_metadata(payload)

    assert metadata["binding_summary"] == "bound_by_topic_continuity"
    assert metadata["plan_summary"]["planning_mode"] == "compare"
    assert metadata["plan_summary"]["step_count"] == 1
    assert metadata["plan_summary"]["fallback_used"] is True
    assert metadata["review_summary"]["matched_target_count"] == 1
    assert metadata["review_summary"]["matched_target_refs"] == ["claim_1"]
    assert metadata["review_summary"]["needs_more_evidence_targets"] == ["claim_2"]
    assert metadata["review_summary"]["follow_up_retrieval_attempted"] is True
    assert metadata["review_summary"]["follow_up_retrieval_sources"] == ["kb/law.md"]
    assert metadata["evidence_summary"]["retrieval_quality_status"] == "bad"
    assert metadata["evidence_summary"]["merged_evidence_count"] == 1
    assert metadata["evidence_summary"]["coverage_query_units"] == 2


def test_agent_registry_metadata_payload_separates_owner_summary_and_convenience_fields() -> None:
    agent = AgentManager()

    metadata = build_registry_metadata_payload(
        owner_summary={
            "binding_summary": "bound_by_topic_continuity",
            "review_summary": {"matched_target_count": 1},
        },
        convenience_fields={
            "channel": "fused",
            "query_unit_ids": ["q1"],
        },
    )

    assert metadata["binding_summary"] == "bound_by_topic_continuity"
    assert metadata["channel"] == "fused"
    assert metadata["workflow_summary"] == {
        "binding_summary": "bound_by_topic_continuity",
        "review_summary": {"matched_target_count": 1},
    }
    assert metadata["registry_convenience"] == {
        "channel": "fused",
        "query_unit_ids": ["q1"],
    }


def test_agent_builds_registry_entries_from_typed_bundle_objects() -> None:
    agent = AgentManager()
    payload = ExecutionPayload(
        route="qa",
        handling_mode="challenge",
        action="respond",
        context_bundle=ContextBundle(binding_summary="bound_by_topic_continuity"),
        plan_bundle=PlanBundle(
            planning_mode="compare",
            query_units=(
                {"unit_id": "q1", "origin": "primary", "text": "试用期依据是什么"},
            ),
        ),
        review_bundle=ReviewBundle(review_mode="challenge_review"),
    )

    entries = build_registry_entries_from_execution_payload(
        payload=payload,
        session_id="session_1",
        tenant_id="tenant_u1",
        group_id="law",
        message="试用期依据是什么",
    )

    object_types = [entry.object_type for entry in entries]
    assert "retrieval_result_ref" not in object_types
    assert object_types.count("question_object") >= 2
    question_entry = entries[0]
    assert question_entry.metadata["workflow_summary"]["binding_summary"] == "bound_by_topic_continuity"
    assert question_entry.metadata["registry_convenience"]["route"] == "qa"
