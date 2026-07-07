from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import graph.agent as agent_module
import pytest
from graph.agent import AgentManager
from graph.serializers.frontend_trace import (
    serialize_execution_payload,
    serialize_intent_analysis,
    serialize_workflow_plan,
)
from intent.schema.intent_types import ControlTrace, IntentModifiers
from workflow.types import ExecutionPayload, WorkflowPlan, WorkflowPolicyFlags
from workflow.types import EvidenceBundle, EvidenceItem


class _Dictable:
    """Small test double for serializer contract tests."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload)


class _IntentAnalysisStub:
    """IntentAnalysis-shaped double so stream tests stay black-box at the boundary."""

    def __init__(self) -> None:
        self.input = _Dictable({"query": "试用期依据是什么"})
        self.evidence = _Dictable({"quality_report": {"status": "good"}})
        self.resolved = _Dictable({"main_intent": "qa"})
        self.control = _Dictable({"handling_mode": "normal"})


class _DispatcherStub:
    """Capture the route request while returning a fixed execution payload."""

    def __init__(self, payload: ExecutionPayload) -> None:
        self.payload = payload
        self.last_plan = None
        self.last_request = None

    def dispatch(self, plan: WorkflowPlan) -> "_DispatcherStub":
        self.last_plan = plan
        return self

    def run(self, plan: WorkflowPlan, request) -> ExecutionPayload:
        self.last_plan = plan
        self.last_request = request
        return self.payload


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
        notes=("trace-test",),
    )


def _make_execution_payload() -> ExecutionPayload:
    return ExecutionPayload(
        route="qa",
        handling_mode="normal",
        action="respond",
        context_bundle={"binding_summary": "not_applicable"},
        plan_bundle={"goal": "试用期依据是什么"},
        review_bundle={"status": "not_applicable"},
        notes=("trace-test",),
    )


def _make_execution_payload_with_evidence() -> ExecutionPayload:
    return ExecutionPayload(
        route="qa",
        handling_mode="normal",
        action="respond",
        context_bundle={"binding_summary": "not_applicable"},
        plan_bundle={"goal": "Science Advances 的 TFA 方法有什么突破"},
        review_bundle={"status": "not_applicable"},
        evidence_bundle=EvidenceBundle(
            query_unit_results=(),
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="ev_1",
                    source_path="storage/groups/medicine/knowledge/raw/documents/pmc_ftp_pdf/undated_f86aeb5405_Sci_Adv.;_10(29)_eado9413/source.pdf",
                    source_type="pdf",
                    locator="page:1 chunk:1",
                    snippet="The effectiveness and practicality of the method was demonstrated by the successful synthesis of several challenging proteins, including the SARS-CoV-2 transmembrane Envelope (E) protein and nanobodies.",
                    channel="fused",
                    score=0.92,
                    query_unit_ids=("primary",),
                ),
            ),
            source_refs=(
                "storage/groups/medicine/knowledge/raw/documents/pmc_ftp_pdf/undated_f86aeb5405_Sci_Adv.;_10(29)_eado9413/source.pdf",
            ),
            coverage_summary={"query_units": 1, "sources": 1},
            quality_summary={"status": "good", "average_weighted_score": 0.9},
            missing_evidence_notes=(),
        ),
        notes=("trace-test",),
    )


def test_frontend_trace_serializers_reuse_existing_contracts() -> None:
    intent_analysis = _IntentAnalysisStub()
    workflow_plan = _make_workflow_plan()
    execution_payload = _make_execution_payload()

    assert serialize_intent_analysis(intent_analysis) == {
        "type": "intent_analysis",
        "input": {"query": "试用期依据是什么"},
        "evidence": {"quality_report": {"status": "good"}},
        "resolved": {"main_intent": "qa"},
        "control": {"handling_mode": "normal"},
    }
    assert serialize_workflow_plan(workflow_plan)["plan"]["route"] == "qa"
    assert serialize_execution_payload(
        execution_payload,
        stage="route_payload_ready",
    ) == {
        "type": "execution_update",
        "stage": "route_payload_ready",
        "payload": execution_payload.to_dict(),
    }


def test_frontend_trace_serializers_fail_loudly_without_to_dict_contract() -> None:
    with pytest.raises(TypeError):
        serialize_workflow_plan(object())

    with pytest.raises(TypeError):
        serialize_execution_payload(object(), stage="route_payload_ready")


def test_agent_astream_emits_frontend_trace_events_before_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent = AgentManager()
    agent.base_dir = tmp_path

    workflow_plan = _make_workflow_plan()
    execution_payload = _make_execution_payload()
    dispatcher = _DispatcherStub(execution_payload)
    agent.workflow_dispatcher = dispatcher

    async def fake_prepare(group_id: str, session_id: str | None, message: str, history: list[dict[str, object]]):
        del group_id, session_id, message, history
        return {"messages": [{"role": "user", "content": "试用期依据是什么"}], "memory_retrieval": {}}

    async def fake_model_answer(messages, extra_instructions=None):
        del messages, extra_instructions
        yield {"type": "token", "content": "根据证据回答。"}
        yield {"type": "done", "content": "根据证据回答。"}

    agent._prepare_messages_for_request = fake_prepare
    agent._load_session_scope = lambda session_id: ("general", ("general",))
    agent._load_recent_registry_entries = lambda **kwargs: []
    agent._emit_intent_event = lambda **kwargs: None
    agent._emit_retrieval_event = lambda **kwargs: None
    agent._emit_answer_event = lambda **kwargs: None
    agent._persist_execution_outputs = lambda **kwargs: None
    agent._astream_model_answer = fake_model_answer

    monkeypatch.setattr(agent_module, "load_group_intent_rule_assets", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_module, "classify_intent", lambda *args, **kwargs: _IntentAnalysisStub())
    monkeypatch.setattr(agent_module, "build_workflow_plan", lambda *args, **kwargs: workflow_plan)
    monkeypatch.setattr(agent_module, "is_knowledge_query", lambda message: False)
    monkeypatch.setattr(agent_module, "build_answer_behavior_rules_from_workflow", lambda plan: ["use workflow"])
    monkeypatch.setattr(agent_module, "build_answer_result_projection_rules_from_workflow", lambda payload: [])

    async def _collect() -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        async for event in agent.astream("试用期依据是什么", [], session_id=None):
            events.append(event)
        return events

    events = asyncio.run(_collect())
    event_types = [event["type"] for event in events]

    assert event_types[:5] == [
        "intent_analysis",
        "workflow_plan",
        "execution_update",
        "token",
        "done",
    ]
    assert events[0]["input"] == {"query": "试用期依据是什么"}
    assert events[0]["evidence"] == {"quality_report": {"status": "good"}}
    assert events[1]["plan"]["route"] == "qa"
    assert events[1]["plan"]["handling_mode"] == "normal"
    assert events[2]["stage"] == "route_payload_ready"
    assert events[2]["payload"]["route"] == "qa"
    assert events[2]["payload"]["action"] == "respond"
    assert "unit_started" not in event_types
    assert "unit_completed" not in event_types
    assert "pause_requested" not in event_types
    assert dispatcher.last_request is not None


def test_agent_astream_knowledge_query_stays_on_workflow_respond_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = AgentManager()
    agent.base_dir = tmp_path

    workflow_plan = _make_workflow_plan()
    execution_payload = _make_execution_payload()
    dispatcher = _DispatcherStub(execution_payload)
    agent.workflow_dispatcher = dispatcher

    async def fake_prepare(group_id: str, session_id: str | None, message: str, history: list[dict[str, object]]):
        del group_id, session_id, message, history
        return {"messages": [{"role": "user", "content": "查知识库, ai发展趋势"}], "memory_retrieval": {}}

    async def fake_model_answer(messages, extra_instructions=None):
        del messages, extra_instructions
        yield {"type": "done", "content": "根据知识库回答。"}

    agent._prepare_messages_for_request = fake_prepare
    agent._load_session_scope = lambda session_id: ("general", ("general",))
    agent._load_recent_registry_entries = lambda **kwargs: []
    agent._emit_intent_event = lambda **kwargs: None
    agent._emit_answer_event = lambda **kwargs: None
    agent._persist_execution_outputs = lambda **kwargs: None
    agent._astream_model_answer = fake_model_answer
    agent._emit_retrieval_event = lambda **kwargs: None

    monkeypatch.setattr(agent_module, "load_group_intent_rule_assets", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_module, "classify_intent", lambda *args, **kwargs: _IntentAnalysisStub())
    monkeypatch.setattr(agent_module, "build_workflow_plan", lambda *args, **kwargs: workflow_plan)
    monkeypatch.setattr(agent_module, "is_knowledge_query", lambda message: True)
    monkeypatch.setattr(agent_module, "build_answer_behavior_rules_from_workflow", lambda plan: ["use workflow"])
    monkeypatch.setattr(agent_module, "build_answer_result_projection_rules_from_workflow", lambda payload: [])

    async def _collect() -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        async for event in agent.astream("查知识库, ai发展趋势", [], session_id=None):
            events.append(event)
        return events

    events = asyncio.run(_collect())

    assert events[1]["plan"]["action"] == "respond"
    assert events[2]["payload"]["action"] == "respond"
    assert events[-1] == {"type": "done", "content": "根据知识库回答。"}


def test_agent_astream_injects_workflow_evidence_into_answer_messages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = AgentManager()
    agent.base_dir = tmp_path

    workflow_plan = _make_workflow_plan()
    execution_payload = _make_execution_payload_with_evidence()
    dispatcher = _DispatcherStub(execution_payload)
    agent.workflow_dispatcher = dispatcher
    observed_messages: list[dict[str, str]] = []

    async def fake_prepare(group_id: str, session_id: str | None, message: str, history: list[dict[str, object]]):
        del group_id, session_id, message, history
        return {"messages": [{"role": "user", "content": "医学问题"}], "memory_retrieval": {}}

    async def fake_model_answer(messages, extra_instructions=None):
        del extra_instructions
        observed_messages.extend(messages)
        yield {"type": "done", "content": "根据证据回答。"}

    agent._prepare_messages_for_request = fake_prepare
    agent._load_session_scope = lambda session_id: ("medicine", ("medicine",))
    agent._load_recent_registry_entries = lambda **kwargs: []
    agent._emit_intent_event = lambda **kwargs: None
    agent._emit_retrieval_event = lambda **kwargs: None
    agent._emit_answer_event = lambda **kwargs: None
    agent._persist_execution_outputs = lambda **kwargs: None
    agent._astream_model_answer = fake_model_answer

    monkeypatch.setattr(agent_module, "load_group_intent_rule_assets", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_module, "classify_intent", lambda *args, **kwargs: _IntentAnalysisStub())
    monkeypatch.setattr(agent_module, "build_workflow_plan", lambda *args, **kwargs: workflow_plan)
    monkeypatch.setattr(agent_module, "is_knowledge_query", lambda message: True)
    monkeypatch.setattr(agent_module, "build_answer_behavior_rules_from_workflow", lambda plan: ["use workflow"])
    monkeypatch.setattr(agent_module, "build_answer_result_projection_rules_from_workflow", lambda payload: [])

    async def _collect() -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        async for event in agent.astream("医学问题", [], session_id="session_1"):
            events.append(event)
        return events

    events = asyncio.run(_collect())

    retrieval_events = [event for event in events if event["type"] == "retrieval"]
    assert retrieval_events
    assert retrieval_events[0]["kind"] == "knowledge"
    assert any(
        message["role"] == "system" and "SARS-CoV-2 transmembrane Envelope (E) protein and nanobodies" in message["content"]
        for message in observed_messages
    )


def test_agent_knowledge_context_reranks_query_matching_pdf_ahead_of_noisy_hits(tmp_path: Path) -> None:
    agent = AgentManager()
    agent.base_dir = tmp_path

    payload = ExecutionPayload(
        route="qa",
        handling_mode="normal",
        action="respond",
        evidence_bundle=EvidenceBundle(
            query_unit_results=(
                {
                    "unit_id": "primary",
                    "query": "医学问题",
                    "selected_query": "Science Advances 2024 TFA native chemical ligation SARS-CoV-2 E protein nanobodies",
                },
            ),
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="noise_1",
                    source_path="storage/groups/medicine/knowledge/raw/documents/yiigle_cn/noise/content.md",
                    source_type="md",
                    locator="paragraph:1 chunk:1",
                    snippet="本期杂志以消化系统疾病为核心主题。",
                    channel="vector",
                    score=200.0,
                    query_unit_ids=("primary",),
                ),
                EvidenceItem(
                    evidence_id="target_1",
                    source_path="storage/groups/medicine/knowledge/raw/documents/pmc_ftp_pdf/undated_f86aeb5405_Sci_Adv.;_10(29)_eado9413/source.pdf",
                    source_type="pdf",
                    locator="page:1 chunk:1",
                    snippet="Enhanced native chemical ligation by peptide conjugation in trifluoroacetic acid ... SARS-CoV-2 transmembrane Envelope (E) protein and nanobodies.",
                    channel="fused",
                    score=20.0,
                    query_unit_ids=("primary",),
                ),
            ),
            source_refs=(),
            coverage_summary={"query_units": 1, "sources": 2},
            quality_summary={"status": "good"},
            missing_evidence_notes=(),
        ),
    )

    context_block = agent._format_knowledge_retrieval_context(payload.evidence_bundle)

    assert "eado9413/source.pdf" in context_block
    assert context_block.index("eado9413/source.pdf") < context_block.index("yiigle_cn/noise/content.md")


def test_agent_astream_fails_loudly_on_legacy_action_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent = AgentManager()
    agent.base_dir = tmp_path

    workflow_plan = _make_workflow_plan()
    execution_payload = _make_execution_payload()
    execution_payload = replace(execution_payload, action="respond")
    dispatcher = _DispatcherStub(execution_payload)
    agent.workflow_dispatcher = dispatcher

    async def fake_prepare(group_id: str, session_id: str | None, message: str, history: list[dict[str, object]]):
        del group_id, session_id, message, history
        return {"messages": [{"role": "user", "content": "测试"}], "memory_retrieval": {}}

    agent._prepare_messages_for_request = fake_prepare
    agent._load_session_scope = lambda session_id: ("general", ("general",))
    agent._load_recent_registry_entries = lambda **kwargs: []
    agent._emit_intent_event = lambda **kwargs: None
    agent._emit_retrieval_event = lambda **kwargs: None
    agent._emit_answer_event = lambda **kwargs: None
    agent._persist_execution_outputs = lambda **kwargs: None

    monkeypatch.setattr(agent_module, "load_group_intent_rule_assets", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_module, "classify_intent", lambda *args, **kwargs: _IntentAnalysisStub())
    monkeypatch.setattr(agent_module, "build_workflow_plan", lambda *args, **kwargs: workflow_plan)
    monkeypatch.setattr(agent_module, "is_knowledge_query", lambda message: False)
    monkeypatch.setattr(agent_module, "build_answer_behavior_rules_from_workflow", lambda plan: ["use workflow"])
    monkeypatch.setattr(agent_module, "build_answer_result_projection_rules_from_workflow", lambda payload: [])
    dispatcher.payload = replace(execution_payload, action="legacy_action")  # type: ignore[arg-type]

    async def _collect() -> None:
        async for _ in agent.astream("测试", [], session_id=None):
            pass

    with pytest.raises(RuntimeError, match="unsupported workflow action emitted by policy/runner: legacy_action"):
        asyncio.run(_collect())


def test_agent_astream_prepares_memory_with_active_group_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agent = AgentManager()
    agent.base_dir = tmp_path

    workflow_plan = _make_workflow_plan()
    execution_payload = _make_execution_payload()
    dispatcher = _DispatcherStub(execution_payload)
    agent.workflow_dispatcher = dispatcher

    observed_group_ids: list[str] = []

    async def fake_prepare(group_id: str, session_id: str | None, message: str, history: list[dict[str, object]]):
        observed_group_ids.append(group_id)
        del session_id, message, history
        return {"messages": [{"role": "user", "content": "医学问题"}], "memory_retrieval": {}}

    async def fake_model_answer(messages, extra_instructions=None):
        del messages, extra_instructions
        yield {"type": "done", "content": "按 medicine 组回答。"}

    agent._prepare_messages_for_request = fake_prepare
    agent._load_session_scope = lambda session_id: ("medicine", ("medicine",))
    agent._load_recent_registry_entries = lambda **kwargs: []
    agent._emit_intent_event = lambda **kwargs: None
    agent._emit_retrieval_event = lambda **kwargs: None
    agent._emit_answer_event = lambda **kwargs: None
    agent._persist_execution_outputs = lambda **kwargs: None
    agent._astream_model_answer = fake_model_answer

    monkeypatch.setattr(agent_module, "load_group_intent_rule_assets", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_module, "classify_intent", lambda *args, **kwargs: _IntentAnalysisStub())
    monkeypatch.setattr(agent_module, "build_workflow_plan", lambda *args, **kwargs: workflow_plan)
    monkeypatch.setattr(agent_module, "is_knowledge_query", lambda message: True)
    monkeypatch.setattr(agent_module, "build_answer_behavior_rules_from_workflow", lambda plan: ["use workflow"])
    monkeypatch.setattr(agent_module, "build_answer_result_projection_rules_from_workflow", lambda payload: [])

    async def _collect() -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        async for event in agent.astream("医学问题", [], session_id="session_1"):
            events.append(event)
        return events

    events = asyncio.run(_collect())

    assert observed_group_ids == ["medicine"]
    assert events[-1] == {"type": "done", "content": "按 medicine 组回答。"}
