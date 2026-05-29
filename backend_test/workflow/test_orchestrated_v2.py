from __future__ import annotations

from intent.schema.intent_types import (
    ContextState,
    ControlSignal,
    ControlTrace,
    DecisionTrace,
    IntentAnalysis,
    IntentInput,
    IntentModifiers,
    ResolvedIntent,
    ResolvedTask,
)
from memory_system.session_working_memory.models import SessionWorkingMemory, WorkingMemoryEntry
from workflow.policy import build_workflow_plan
from workflow.powers.planning_power import PlanningPower
from workflow.routes.base import RouteExecutionRequest
from workflow.types import ContextBindingResult, ExecutionGraph, ExecutionUnit, GlobalBindingFrame
from workflow.workers.execution_worker import ExecutionWorker
from workflow.workers.global_binding_worker import GlobalBindingWorker
from workflow.workers.planner_worker import PlannerWorker


def _make_analysis(
    *,
    query: str,
    route: str = "orchestrated",
    task_complexity: str = "simple",
    task_shape: str = "single_question",
    task_topology: str = "single",
    capabilities: tuple[str, ...] = (),
    context_dependency: str = "none",
    ambiguity_states: tuple[str, ...] = (),
) -> IntentAnalysis:
    modifiers = IntentModifiers()
    trace = ControlTrace(
        main_intent="qa",
        modifiers=modifiers,
        task_complexity=task_complexity,
        task_shape=task_shape,
        task_topology=task_topology,
        context_dependency=context_dependency,
        ambiguity_states=ambiguity_states,
        missing_context_types=(),
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    return IntentAnalysis(
        input=IntentInput(user_query=query, context_state=ContextState()),
        evidence=None,  # type: ignore[arg-type]
        resolved=ResolvedIntent(
            main_intent="qa",
            modifiers=modifiers,
            task=ResolvedTask(
                complexity=task_complexity,
                shape=task_shape,
                topology=task_topology,
            ),
            context_dependency=context_dependency,
            decision=DecisionTrace(strength="high", source="rule", reason="test"),
        ),
        control=ControlSignal(
            route=route,  # type: ignore[arg-type]
            handling_mode="normal",
            capabilities=capabilities,  # type: ignore[arg-type]
            trace=trace,
        ),
    )


class _FakeBindingPower:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def collect_candidates(self, entries, *, limit: int = 20):
        del limit
        return [dict(item) for item in entries]

    def bind(self, query, candidates, **kwargs):
        del kwargs
        normalized_candidates = [dict(item) for item in candidates]
        self.calls.append({"query": query, "candidate_count": len(normalized_candidates)})
        target = normalized_candidates[0] if normalized_candidates else {"object_id": "fallback_target", "content": query}
        return ContextBindingResult(
            relevant_set=tuple(normalized_candidates),
            bound_targets=(target,),
            resolved_target_ids=(str(target.get("object_id") or target.get("content") or ""),),
            binding_confidence="high",
            binding_summary="binding_applied",
            rewritten_query=f"{target.get('content', '')} {query}".strip(),
        )


class _ClarifyingBindingPower(_FakeBindingPower):
    def bind(self, query, candidates, **kwargs):
        del candidates, kwargs
        self.calls.append({"query": query, "candidate_count": 0})
        return ContextBindingResult(
            binding_confidence="low",
            binding_summary="needs_clarification",
            needs_clarification=True,
            binding_ambiguous=True,
            fallback_type="needs_clarification",
            reason="multiple_relevant_targets",
        )


class _FakeRetrievalPower:
    def __init__(self, *, average_score: float = 0.8, repaired_units: int = 0) -> None:
        self.average_score = average_score
        self.repaired_units = repaired_units
        self.calls: list[str] = []

    def retrieve(self, query_units):
        from workflow.types import EvidenceBundle, EvidenceItem, RetrievalUnitResult

        unit = tuple(query_units)[0]
        self.calls.append(unit.text)
        status = "good" if self.average_score >= 0.75 else "weak" if self.average_score >= 0.45 else "bad"
        return EvidenceBundle(
            query_unit_results=(
                RetrievalUnitResult(
                    unit_id=unit.unit_id,
                    query=unit.text,
                    origin="primary",
                    quality={"status": status, "weighted_score": self.average_score},
                    evidence_count=1,
                    selected_query=unit.text,
                    selected_mode="raw",
                    retrieval_status=status,
                    fallback_used=False,
                ),
            ),
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="ev_1",
                    source_path="notes/sample.md",
                    source_type="note",
                    locator="1",
                    snippet="sample evidence",
                    channel="local",
                    score=self.average_score,
                    query_unit_ids=(unit.unit_id,),
                ),
            ),
            source_refs=("notes/sample.md",),
            coverage_summary={"query_units": 1, "sources": 1},
            quality_summary={
                "average_weighted_score": self.average_score,
                "status": status,
                "repairable_units": 0,
                "repaired_units": self.repaired_units,
            },
            missing_evidence_notes=() if status != "bad" else ("retrieval_quality_weak",),
        )


class _FakeReviewWorker:
    def retrieval_quality_check(self, *, evidence_bundle):
        return {
            "status": evidence_bundle.quality_summary.get("status", "unknown"),
            "repairable_units": evidence_bundle.quality_summary.get("repairable_units", 0),
            "repaired_units": evidence_bundle.quality_summary.get("repaired_units", 0),
        }


def test_simple_compare_route_falls_back_to_qa() -> None:
    analysis = _make_analysis(
        query="比较A和B哪个好",
        task_complexity="simple",
        task_shape="compare",
        task_topology="single",
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=False,
        active_group_id="law",
        allowed_group_ids=("law",),
    )

    assert plan.route == "qa"
    assert plan.use_planner is False


def test_staged_route_stays_orchestrated() -> None:
    analysis = _make_analysis(
        query="先判断这个需求是否需要改schema，如果要改，再说会影响哪些接口",
        task_complexity="simple",
        task_shape="verify",
        task_topology="staged",
    )

    plan = build_workflow_plan(
        analysis,
        is_knowledge_query=False,
        active_group_id="law",
        allowed_group_ids=("law",),
    )

    assert plan.route == "orchestrated"
    assert plan.use_planner is True


def test_global_binding_frame_marks_partial_context_scope() -> None:
    worker = GlobalBindingWorker()

    frame = worker.build_frame(
        query="刚才那个结论具体指什么？再列一下劳动合同法第19条依据",
        candidates=[{"object_id": "question_1", "content": "刚才那个结论"}],
        recent_messages=[{"role": "assistant", "content": "前面提到过一个结论。"}],
    )

    assert frame.binding_scope_hint == "partial"
    assert frame.recommended_binding_mode == "selective_per_unit"


def test_global_binding_frame_keeps_none_for_fresh_parallel_queries() -> None:
    worker = GlobalBindingWorker()

    frame = worker.build_frame(
        query="分别比较A和B，再说哪个更可行",
        candidates=[],
        recent_messages=[],
    )

    assert frame.binding_scope_hint == "none"
    assert frame.recommended_binding_mode == "skip"


def test_global_binding_frame_prefers_llm_structured_result_when_available() -> None:
    worker = GlobalBindingWorker()

    def llm_call(prompt: str) -> str:
        assert "working_memory_hints" in prompt
        return """
        {
          "query_is_context_dependent": true,
          "binding_scope_hint": "global",
          "shared_target_candidates": ["question_1"],
          "recommended_binding_mode": "global_only",
          "segment_hints": [
            {"text": "把刚才那个结论展开一下", "needs_context": true, "shared_target_candidate_ids": ["question_1"], "reason": "shared target"}
          ],
          "notes": ["llm_frame"]
        }
        """

    frame = worker.build_frame(
        query="把刚才那个结论展开一下",
        candidates=[{"object_id": "question_1", "content": "刚才那个结论"}],
        recent_messages=[{"role": "assistant", "content": "前面提到过一个结论。"}],
        working_memory=SessionWorkingMemory(
            entries=[
                WorkingMemoryEntry(
                    entry_id="wm_focus",
                    entry_type="focus_task",
                    turn_id="turn_1",
                    source_kind="assistant",
                    source_ref="assistant:1",
                    content="展开刚才的结论并核验依据",
                    confidence="high",
                )
            ]
        ),
        llm_call=llm_call,
    )

    assert frame.binding_scope_hint == "global"
    assert frame.recommended_binding_mode == "global_only"
    assert frame.segment_hints[0]["needs_context"] is True
    assert "llm_frame" in frame.notes


def test_global_binding_frame_coerces_invalid_global_mode_without_shared_target() -> None:
    worker = GlobalBindingWorker()

    def llm_call(prompt: str) -> str:
        assert "segment_hints" in prompt
        return """
        {
          "query_is_context_dependent": true,
          "binding_scope_hint": "global",
          "shared_target_candidates": [],
          "recommended_binding_mode": "global_only",
          "segment_hints": [
            {"text": "把刚才那个结论展开一下", "needs_context": true, "shared_target_candidate_ids": [], "reason": "needs context"}
          ],
          "notes": ["llm_frame"]
        }
        """

    frame = worker.build_frame(
        query="把刚才那个结论展开一下",
        candidates=[],
        recent_messages=[{"role": "assistant", "content": "前面提到过一个结论。"}],
        llm_call=llm_call,
    )

    assert frame.binding_scope_hint == "global"
    assert frame.recommended_binding_mode == "selective_per_unit"
    assert frame.segment_hints


def test_planner_outputs_dag_for_staged_execution_graph() -> None:
    power = PlanningPower()
    bundle = power.build_plan_bundle_obj(
        query="先判断是否要改schema，如果要改，再分析影响接口",
        task_shape="verify",
        task_topology="staged",
        global_binding_frame=GlobalBindingFrame(),
        binding_enabled=False,
        planner_worker=PlannerWorker(),
    )

    graph = bundle.execution_graph_obj()
    plan_payload = bundle.to_dict()

    assert graph.is_dag() is True
    assert plan_payload["plan_summary"]["dag"] is True
    assert plan_payload["plan_summary"]["execution_unit_count"] >= 2
    assert any(edge["edge_type"] == "conditional" for edge in plan_payload["execution_graph"]["edges"])


def test_execution_worker_uses_pre_shared_binding_for_global_target() -> None:
    binding_power = _FakeBindingPower()
    worker = ExecutionWorker()
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(
                unit_id="unit_1",
                goal="展开这个结论",
                capability="qa_like",
                binding_mode="pre_shared",
                output_slot="answer",
            ).to_dict(),
        ),
        edges=(),
    )
    request = RouteExecutionRequest(message="展开这个结论", messages=[{"role": "user", "content": "展开这个结论"}], context={})

    result = worker.execute(
        execution_graph=graph,
        request=request,
        binding_candidates=[
            {"object_id": "question_1", "content": "这个结论"},
            {"object_id": "question_2", "content": "另一个结论"},
        ],
        global_binding_frame=GlobalBindingFrame(
            query_is_context_dependent=True,
            binding_scope_hint="global",
            shared_target_candidates=("question_1",),
            recommended_binding_mode="global_only",
        ),
        context_binding_power=binding_power,
        binding_enable_flag=True,
    )

    assert result.unit_results[0].used_binding is True
    assert binding_power.calls[0]["candidate_count"] == 1


def test_execution_worker_uses_lazy_binding_for_partial_scope() -> None:
    binding_power = _FakeBindingPower()
    worker = ExecutionWorker()
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(
                unit_id="unit_1",
                goal="刚才那个结论具体指什么",
                capability="qa_like",
                binding_mode="lazy",
                output_slot="answer",
            ).to_dict(),
        ),
        edges=(),
    )
    request = RouteExecutionRequest(
        message="刚才那个结论具体指什么",
        messages=[{"role": "user", "content": "刚才那个结论具体指什么"}],
        context={"recent_messages": [{"role": "assistant", "content": "之前提过两个结论。"}]},
    )

    result = worker.execute(
        execution_graph=graph,
        request=request,
        binding_candidates=[
            {"object_id": "question_1", "content": "第一个结论"},
            {"object_id": "question_2", "content": "第二个结论"},
        ],
        global_binding_frame=GlobalBindingFrame(
            query_is_context_dependent=True,
            binding_scope_hint="partial",
            shared_target_candidates=("question_1", "question_2"),
            recommended_binding_mode="selective_per_unit",
        ),
        context_binding_power=binding_power,
        binding_enable_flag=True,
    )

    assert result.unit_results[0].used_binding is True
    assert binding_power.calls[0]["candidate_count"] == 2


def test_execution_worker_blocks_retrieval_when_binding_needs_clarification() -> None:
    binding_power = _ClarifyingBindingPower()
    retrieval_power = _FakeRetrievalPower()
    worker = ExecutionWorker()
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(
                unit_id="unit_1",
                goal="刚才那个结论具体指什么",
                capability="qa_like",
                binding_mode="lazy",
                output_slot="answer",
            ).to_dict(),
        ),
        edges=(),
    )
    request = RouteExecutionRequest(
        message="刚才那个结论具体指什么",
        messages=[{"role": "user", "content": "刚才那个结论具体指什么"}],
        context={"recent_messages": [{"role": "assistant", "content": "之前提过两个结论。"}]},
    )

    result = worker.execute(
        execution_graph=graph,
        request=request,
        binding_candidates=[
            {"object_id": "question_1", "content": "第一个结论"},
            {"object_id": "question_2", "content": "第二个结论"},
        ],
        global_binding_frame=GlobalBindingFrame(
            query_is_context_dependent=True,
            binding_scope_hint="partial",
            shared_target_candidates=("question_1", "question_2"),
            recommended_binding_mode="selective_per_unit",
        ),
        context_binding_power=binding_power,
        retrieval_power=retrieval_power,
        review_worker=_FakeReviewWorker(),
        binding_enable_flag=True,
        allow_retrieval=True,
    )

    assert result.unit_results[0].state == "blocked"
    assert result.unit_results[0].skipped_reason == "binding_needs_clarification"
    assert retrieval_power.calls == []
    assert "binding_needs_clarification" in result.key_events


def test_execution_worker_degrades_weak_retrieval_and_skips_conditional_downstream() -> None:
    worker = ExecutionWorker()
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(
                unit_id="unit_verify",
                goal="先判断这个需求是否值得做",
                capability="verify",
                binding_mode="skip",
                output_slot="verify_result",
            ).to_dict(),
            ExecutionUnit(
                unit_id="unit_synthesis",
                goal="如果值得做，再总结落地建议",
                capability="synthesis",
                depends_on=("unit_verify",),
                proceed_if="all_dependencies_completed",
                output_slot="final_answer",
            ).to_dict(),
        ),
        edges=(
            {
                "from_unit_id": "unit_verify",
                "to_unit_id": "unit_synthesis",
                "edge_type": "conditional",
                "condition": "all_dependencies_completed",
            },
        ),
    )
    request = RouteExecutionRequest(
        message="先判断这个需求是否值得做，如果值得做，再总结落地建议",
        messages=[{"role": "user", "content": "先判断这个需求是否值得做，如果值得做，再总结落地建议"}],
        context={},
    )

    result = worker.execute(
        execution_graph=graph,
        request=request,
        binding_candidates=[],
        global_binding_frame=GlobalBindingFrame(),
        retrieval_power=_FakeRetrievalPower(average_score=0.2),
        review_worker=_FakeReviewWorker(),
        binding_enable_flag=False,
        allow_retrieval=True,
    )

    assert result.unit_results[0].state == "degraded"
    assert result.unit_results[0].skipped_reason == "retrieval_quality_bad"
    assert result.unit_results[1].state == "skipped"
    assert result.unit_results[1].skipped_reason == "dependency_not_completed"
    assert "retrieval_quality_weak" in result.key_events


def test_execution_worker_uses_capability_executor_notes_for_working_memory_consumption() -> None:
    worker = ExecutionWorker()
    graph = ExecutionGraph(
        units=(
            ExecutionUnit(
                unit_id="unit_verify",
                goal="检查这条说法是否成立",
                capability="verify",
                binding_mode="skip",
                output_slot="verify_result",
            ).to_dict(),
            ExecutionUnit(
                unit_id="unit_synthesis",
                goal="总结最终回答",
                capability="synthesis",
                depends_on=("unit_verify",),
                proceed_if="all_dependencies_completed",
                output_slot="final_answer",
            ).to_dict(),
        ),
        edges=(
            {"from_unit_id": "unit_verify", "to_unit_id": "unit_synthesis", "edge_type": "depends_on"},
        ),
    )
    working_memory = SessionWorkingMemory(
        entries=[
            WorkingMemoryEntry(
                entry_id="wm_assert",
                entry_type="user_assertion",
                turn_id="turn_1",
                source_kind="user",
                source_ref="user:1",
                content="这个结论依据不足",
                confidence="high",
            ),
            WorkingMemoryEntry(
                entry_id="wm_answer_unit",
                entry_type="answer_unit",
                turn_id="turn_1",
                source_kind="assistant",
                source_ref="assistant:1",
                content="之前的回答结论是A更稳妥。",
                confidence="high",
            ),
        ],
    )
    request = RouteExecutionRequest(
        message="检查这条说法是否成立并总结",
        messages=[{"role": "user", "content": "检查这条说法是否成立并总结"}],
        context={"working_memory": working_memory.to_dict()},
    )

    result = worker.execute(
        execution_graph=graph,
        request=request,
        binding_candidates=[],
        global_binding_frame=GlobalBindingFrame(),
        retrieval_power=_FakeRetrievalPower(average_score=0.8),
        review_worker=_FakeReviewWorker(),
        binding_enable_flag=False,
        allow_retrieval=True,
    )

    assert "user_assertion_consumed" in result.unit_results[0].notes
    assert "answer_unit_consumed" in result.unit_results[1].notes
