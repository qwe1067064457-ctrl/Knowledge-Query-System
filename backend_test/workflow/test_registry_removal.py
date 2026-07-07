from __future__ import annotations

import asyncio
from pathlib import Path

import graph.agent as agent_module
from context.assembly.context_manager import ContextManager
from context.session.session_manager import SessionManager
from graph.agent import AgentManager
from intent.schema.intent_types import ControlTrace, IntentModifiers
from memory_system import MemorySystem
from workflow.runners.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import EvidenceBundle, EvidenceItem, ExecutionPayload, WorkflowPlan, WorkflowPolicyFlags


class _DispatcherStub:
    """Capture the route request so tests can assert runtime context boundaries."""

    def __init__(self, payload: ExecutionPayload) -> None:
        self.payload = payload
        self.last_request = None

    def dispatch(self, plan: WorkflowPlan) -> "_DispatcherStub":
        del plan
        return self

    def run(self, plan: WorkflowPlan, request) -> ExecutionPayload:
        del plan
        self.last_request = request
        return self.payload


class _IntentAnalysisStub:
    def __init__(self) -> None:
        self.input = _Dictable({"query": "那个依据呢"})
        self.evidence = _Dictable({"quality_report": {"status": "good"}})
        self.resolved = _Dictable({"main_intent": "qa"})
        self.control = _Dictable({"handling_mode": "normal"})


class _Dictable:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload)


class _InspectableRunner(BaseRouteRunner):
    pass


def _make_workflow_plan() -> WorkflowPlan:
    trace = ControlTrace(
        main_intent="qa",
        modifiers=IntentModifiers(),
        task_complexity="simple",
        task_shape="single_question",
        task_topology="single",
        context_dependency="none",
        ambiguity_states=(),
        missing_context_types=(),
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    return WorkflowPlan(
        route="qa",
        handling_mode="normal",
        action="respond",
        use_context=False,
        cite_sources=True,
        use_planner=False,
        decompose_query=False,
        rewrite_query=False,
        should_ask_clarification_first=False,
        trace=trace,
        enabled_powers=("retrieval_power",),
        policy_flags=WorkflowPolicyFlags(),
        notes=("registry-removal-test",),
    )


def _make_execution_payload() -> ExecutionPayload:
    return ExecutionPayload(
        route="qa",
        handling_mode="normal",
        action="respond",
        context_bundle={"binding_summary": "not_applicable"},
        plan_bundle={"goal": "那个依据呢"},
        review_bundle={"status": "not_applicable"},
        evidence_bundle=EvidenceBundle(
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="ev_1",
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


def test_base_route_runner_ignores_legacy_registry_candidates() -> None:
    runner = _InspectableRunner()
    request = RouteExecutionRequest(
        message="那个依据呢",
        messages=[{"role": "user", "content": "那个依据呢"}],
        context={
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "你刚才那个依据是什么？",
                    "refs": ["evidence_1"],
                },
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "劳动合同法第19条。",
                    "refs": ["docs/law.md"],
                },
            ]
        },
    )

    assert runner._registry_candidates(request) == []
    assert runner._registry_binding_candidates(request) == []
    assert runner._registry_evidence_candidates(request) == []


def test_agent_astream_does_not_inject_registry_entries_into_runtime_request(
    tmp_path: Path,
    monkeypatch,
) -> None:
    agent = AgentManager()
    agent.base_dir = tmp_path
    dispatcher = _DispatcherStub(_make_execution_payload())
    agent.workflow_dispatcher = dispatcher

    async def fake_prepare(group_id: str, session_id: str | None, message: str, history: list[dict[str, object]]):
        del group_id, session_id, message, history
        return {"messages": [{"role": "user", "content": "那个依据呢"}], "memory_retrieval": {}}

    async def fake_model_answer(messages, extra_instructions=None):
        del messages, extra_instructions
        yield {"type": "done", "content": "根据证据回答。"}

    agent._prepare_messages_for_request = fake_prepare
    agent._load_session_scope = lambda session_id: ("law", ("law",))
    agent._load_recent_registry_entries = lambda **kwargs: [
        {
            "object_id": "legacy_question",
            "object_type": "question_object",
            "content": "这是旧 registry 条目",
            "source_power": "workflow",
        }
    ]
    agent._emit_intent_event = lambda **kwargs: None
    agent._emit_retrieval_event = lambda **kwargs: None
    agent._emit_answer_event = lambda **kwargs: None
    agent._persist_execution_outputs = lambda **kwargs: None
    agent._astream_model_answer = fake_model_answer

    monkeypatch.setattr(agent_module, "load_group_intent_rule_assets", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_module, "classify_intent", lambda *args, **kwargs: _IntentAnalysisStub())
    monkeypatch.setattr(agent_module, "build_workflow_plan", lambda *args, **kwargs: _make_workflow_plan())
    monkeypatch.setattr(agent_module, "is_knowledge_query", lambda message: False)
    monkeypatch.setattr(agent_module, "build_answer_behavior_rules_from_workflow", lambda plan: ["use workflow"])
    monkeypatch.setattr(agent_module, "build_answer_result_projection_rules_from_workflow", lambda payload: [])

    async def _collect() -> None:
        async for _ in agent.astream("那个依据呢", [], session_id="session_1"):
            pass

    asyncio.run(_collect())

    assert dispatcher.last_request is not None
    assert "registry_entries" not in dispatcher.last_request.context
    assert "recent_power" not in dispatcher.last_request.context
    assert "recent_object_type" not in dispatcher.last_request.context


def test_agent_persist_execution_payload_no_longer_writes_registry_by_default(tmp_path: Path) -> None:
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

    agent._persist_execution_payload(
        payload=_make_execution_payload(),
        session_id=session.id,
        group_id="law",
        message="那个依据呢",
    )

    registry = context_manager.load_registry(
        tenant_id="tenant_u1",
        group_id="law",
        agent_id="default",
        session_id=session.id,
    )
    assert registry.entries == ()
