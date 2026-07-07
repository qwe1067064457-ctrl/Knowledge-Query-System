from __future__ import annotations

from intent.schema.intent_types import ControlTrace, IntentModifiers
from workflow.runners.base import RouteExecutionRequest
from workflow.runners.qa_runner import QaRouteRunner
from workflow.types import EvidenceBundle, EvidenceItem, WorkflowPlan, WorkflowPolicyFlags


class _FakeRetrievalPower:
    def __init__(self) -> None:
        self.last_query_units = []
        self.last_path_filters = ()

    def retrieve(self, query_units, *, top_k: int = 4, path_filters=()) -> EvidenceBundle:
        del top_k
        self.last_query_units = list(query_units)
        self.last_path_filters = tuple(path_filters)
        return EvidenceBundle(
            query_unit_results=tuple(
                {
                    "unit_id": unit.unit_id,
                    "query": unit.text,
                    "origin": unit.origin,
                }
                for unit in query_units
            ),
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="evidence_1",
                    source_path="storage/groups/law/knowledge/docs/law.md",
                    source_type="official_structured",
                    locator="section-19",
                    snippet="一年期合同试用期上限一个月。",
                    channel="vector",
                    score=0.92,
                    query_unit_ids=tuple(unit.unit_id for unit in query_units),
                ),
            ),
            source_refs=("storage/groups/law/knowledge/docs/law.md",),
            coverage_summary={"query_units": len(query_units), "sources": 1},
            quality_summary={"average_weighted_score": 0.92},
            missing_evidence_notes=(),
        )


def _make_plan(*, enabled_powers: tuple[str, ...], handling_mode: str = "normal") -> WorkflowPlan:
    trace = ControlTrace(
        main_intent="qa",
        modifiers=IntentModifiers(challenge=handling_mode == "challenge"),
        task_complexity="simple",
        task_shape="single_question",
        task_topology="single",
        context_dependency="previous_answer" if "context_binding_power" in enabled_powers else "none",
        ambiguity_states=("history_dependent",) if "context_binding_power" in enabled_powers else (),
        missing_context_types=(),
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    return WorkflowPlan(
        route="qa",
        handling_mode=handling_mode,  # type: ignore[arg-type]
        action="respond",
        use_context="context_binding_power" in enabled_powers,
        cite_sources=True,
        use_planner=False,
        decompose_query=False,
        rewrite_query="context_binding_power" in enabled_powers,
        should_ask_clarification_first=False,
        trace=trace,
        enabled_powers=enabled_powers,  # type: ignore[arg-type]
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(
            need_context_binding="context_binding_power" in enabled_powers,
            need_retrieval="retrieval_power" in enabled_powers,
        ),
        notes=("qa-route-slim",),
    )


def test_qa_route_keeps_retrieval_and_evidence_bundle() -> None:
    runner = QaRouteRunner()
    runner.retrieval_power = _FakeRetrievalPower()
    plan = _make_plan(enabled_powers=("retrieval_power",))
    request = RouteExecutionRequest(
        message="试用期上限是什么？",
        messages=[{"role": "user", "content": "试用期上限是什么？"}],
        is_knowledge_query=True,
        context={"active_group_id": "law"},
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert payload.evidence_bundle is not None
    assert payload.evidence_bundle.source_ref_list() == ["storage/groups/law/knowledge/docs/law.md"]
    assert payload.context_bundle["binding"] is None
    assert payload.review_bundle["status"] == "not_applicable"
    assert "retrieval_performed" in payload.key_events
    assert runner.retrieval_power.last_query_units[0].text
    assert runner.retrieval_power.last_path_filters == ("storage/groups/law/knowledge",)


def test_qa_route_ignores_context_binding_and_challenge_powers_even_if_requested() -> None:
    runner = QaRouteRunner()
    runner.retrieval_power = _FakeRetrievalPower()
    plan = _make_plan(
        enabled_powers=("retrieval_power", "context_binding_power", "challenge_power"),
        handling_mode="challenge",
    )
    request = RouteExecutionRequest(
        message="你刚才这个依据是什么？",
        messages=[{"role": "user", "content": "你刚才这个依据是什么？"}],
        is_knowledge_query=True,
        context={
            "active_group_id": "law",
            "registry_entries": [
                {
                    "object_id": "legacy_question",
                    "object_type": "question_object",
                    "content": "这是旧 registry 里的上下文",
                    "refs": ["legacy_evidence"],
                }
            ],
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert payload.context_bundle["binding"] is None
    assert payload.context_bundle["candidate_count"] == 0
    assert payload.review_bundle["status"] == "not_applicable"
    assert "binding_applied" not in payload.key_events
    assert "binding_ambiguous" not in payload.key_events
    assert "clarification_required" not in payload.key_events
