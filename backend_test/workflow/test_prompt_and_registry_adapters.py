from __future__ import annotations

from pathlib import Path

from graph.prompt_builders.answer_prompt_assembler import (
    assemble_answer_messages,
    build_answer_system_prompt,
)
from graph.prompt_builders.workflow_prompt_projector import (
    build_answer_behavior_rules_from_workflow,
    build_answer_result_projection_rules_from_workflow,
)
from workflow.adapters.workflow_registry_consumer import (
    binding_candidates,
    evidence_candidates,
)
from workflow.adapters.workflow_registry_projection import (
    build_registry_entries_from_execution_payload,
)
from workflow.types import (
    ContextBindingResult,
    ContextBundle,
    EvidenceBundle,
    EvidenceItem,
    ExecutionPayload,
    PlanBundle,
    WorkflowPlan,
)
from intent.schema.intent_types import ControlTrace


def _make_plan(**overrides) -> WorkflowPlan:
    payload = {
        "route": "qa",
        "handling_mode": "normal",
        "action": "respond",
        "use_context": True,
        "cite_sources": False,
        "use_planner": False,
        "decompose_query": False,
        "rewrite_query": False,
        "should_ask_clarification_first": False,
        "trace": ControlTrace(main_intent="chat"),
        "enabled_powers": (),
        "knowledge_scope_status": "resolved",
        "notes": (),
    }
    payload.update(overrides)
    return WorkflowPlan(**payload)


def test_answer_prompt_assembler_combines_system_override_and_messages(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts" / "system"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.joinpath("answer_system_prompt.md").write_text("Base system prompt.", encoding="utf-8")
    prompts_dir.joinpath("runtime_override.md").write_text("Runtime Override", encoding="utf-8")
    context_dir = tmp_path / "context" / "assembly"
    context_dir.mkdir(parents=True, exist_ok=True)
    context_dir.joinpath("context_policy.json").write_text(
        '{"prompt":{"system_prompt_path":"prompts/system/answer_system_prompt.md"}}',
        encoding="utf-8",
    )

    messages = assemble_answer_messages(
        tmp_path,
        [{"role": "user", "content": "你好"}],
        rag_mode=False,
        extra_instructions=["Workflow behavior"],
    )

    assert messages[0]["role"] == "system"
    assert "Base system prompt." in messages[0]["content"]
    assert "Runtime Override" in messages[0]["content"]
    assert "Workflow behavior" in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "你好"}


def test_answer_prompt_assembler_falls_back_when_prompt_missing(tmp_path: Path) -> None:
    context_dir = tmp_path / "context" / "assembly"
    context_dir.mkdir(parents=True, exist_ok=True)
    context_dir.joinpath("context_policy.json").write_text(
        '{"prompt":{"system_prompt_path":"prompts/system/missing.md"}}',
        encoding="utf-8",
    )

    prompt = build_answer_system_prompt(tmp_path, rag_mode=False)

    assert "核心问答助手" in prompt
    assert "不要编造事实" in prompt


def test_workflow_prompt_projector_emits_behavior_and_result_rules() -> None:
    plan = _make_plan(
        route="orchestrated",
        handling_mode="challenge",
        cite_sources=True,
        use_planner=True,
        decompose_query=True,
    )
    behavior_rules = build_answer_behavior_rules_from_workflow(plan)
    payload = ExecutionPayload(
        route="qa",
        handling_mode="challenge",
        action="respond",
        context_bundle={"binding_summary": "bound_by_topic_continuity"},
        plan_bundle={
            "planning_mode": "compare",
            "ordered_steps": [{"title": "Compare", "sequence": 1}],
            "execution_checkpoints": [{"name": "coverage"}],
            "fallback_used": True,
        },
        review_bundle={
            "review_mode": "challenge_review",
            "review_confidence": "medium",
            "review_scope": "single_target",
            "review_summary": {
                "status_summary": "partial_success",
                "needs_more_evidence_targets": ["claim_2"],
                "follow_up_retrieval_attempted": True,
            },
        },
        evidence_bundle=EvidenceBundle(
            quality_summary={"status": "bad"},
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="e1",
                    source_path="docs/law.md",
                    source_type="official_structured",
                    locator="p1",
                    snippet="劳动合同法第19条。",
                    channel="fused",
                    score=0.9,
                ),
            ),
            source_refs=("docs/law.md",),
            missing_evidence_notes=("weak",),
        ),
    )

    result_rules = build_answer_result_projection_rules_from_workflow(payload)

    assert any("challenge/correction" in item for item in behavior_rules)
    assert any("stages or subtask order visible" in item for item in behavior_rules)
    assert any("citations" in item for item in behavior_rules)
    assert any("binding summary" in item for item in result_rules)
    assert any("planning summary" in item for item in result_rules)
    assert any("review summary" in item for item in result_rules)
    assert any("evidence summary" in item for item in result_rules)


def test_workflow_prompt_projector_skips_not_applicable_result_rules() -> None:
    payload = ExecutionPayload(route="chat", handling_mode="normal", action="respond")

    result_rules = build_answer_result_projection_rules_from_workflow(payload)

    assert result_rules == []


def test_workflow_registry_projection_uses_evidence_ref_and_keeps_summary_layers() -> None:
    payload = ExecutionPayload(
        route="qa",
        handling_mode="normal",
        action="respond",
        context_bundle=ContextBundle(binding_summary="bound_by_topic_continuity"),
        plan_bundle=PlanBundle(
            query_units=({"unit_id": "q1", "origin": "primary", "text": "试用期依据是什么"},),
        ),
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
                    query_unit_ids=("q1",),
                ),
            ),
            source_refs=("docs/law.md",),
        ),
    )

    entries = build_registry_entries_from_execution_payload(
        payload=payload,
        session_id="session_1",
        tenant_id="tenant_u1",
        group_id="law",
        message="试用期依据是什么",
    )

    object_types = {entry.object_type for entry in entries}
    assert object_types == {"question_object", "evidence_ref"}
    assert "evidence_ref" in object_types
    assert "retrieval_result_ref" not in object_types
    evidence_entry = next(entry for entry in entries if entry.object_type == "evidence_ref")
    assert evidence_entry.metadata["workflow_summary"]["binding_summary"] == "bound_by_topic_continuity"
    assert evidence_entry.metadata["registry_convenience"]["channel"] == "fused"
    question_entries = [entry for entry in entries if entry.object_type == "question_object"]
    assert len(question_entries) == 2
    assert question_entries[0].refs == ()
    assert question_entries[1].metadata["registry_convenience"]["unit_id"] == "q1"


def test_workflow_registry_consumer_applies_type_specific_rules() -> None:
    entries = [
        {"object_type": "question_object", "content": "B", "metadata": {"workflow_summary": {}, "registry_convenience": {"route": "qa"}}},
        {"object_type": "evidence_ref", "content": "D", "refs": ["docs/law.md", "p1"], "metadata": {"workflow_summary": {}, "registry_convenience": {"channel": "fused"}}},
    ]

    binding = binding_candidates(entries)
    evidence = evidence_candidates(entries)

    assert {item["object_type"] for item in binding} == {"question_object"}
    assert len(evidence) == 1
    assert evidence[0].channel == "fused"


def test_workflow_registry_consumer_does_not_treat_convenience_metadata_as_reasoning_object() -> None:
    entries = [
        {
            "object_type": "evidence_ref",
            "content": "劳动合同法第19条。",
            "refs": ["docs/law.md", "p1"],
            "metadata": {
                "workflow_summary": {"binding_summary": "bound_by_topic_continuity"},
                "registry_convenience": {"channel": "fused", "query_unit_ids": ["q1"]},
            },
        }
    ]

    assert binding_candidates(entries) == []
