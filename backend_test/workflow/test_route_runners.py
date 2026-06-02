from __future__ import annotations

from datetime import datetime

from context.models import MemoryEntry, TranscriptEntry
from context.session import DEFAULT_AGENT, SessionManager
from memory_system.memory_anchor import MemoryAnchorBuilder
from memory_system.session_working_memory.models import SessionWorkingMemory, WorkingMemoryEntry, WorkingMemoryHead
from intent.schema.intent_types import ControlTrace, IntentModifiers
from workflow.runners.base import RouteExecutionRequest
from workflow.runners.chat_runner import ChatRouteRunner
from workflow.runners.orchestrated_runner import OrchestratedRouteRunner
from workflow.runners.qa_runner import QaRouteRunner
from workflow.runners.reject_runner import RejectRouteRunner
from workflow.types import ChallengeResult, EvidenceAssessmentResult, EvidenceBundle, EvidenceItem, EvidenceRefCandidate, ReviewEvaluationResult, WorkflowPlan, WorkflowPolicyFlags


class _FakeRetrievalPower:
    def __init__(self) -> None:
        self.last_query_units = []

    def retrieve(self, query_units, *, top_k: int = 4) -> EvidenceBundle:
        del top_k
        self.last_query_units = list(query_units)
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
                    evidence_id="evidence_2",
                    source_path="kb/law.md",
                    source_type="official_structured",
                    locator="section-19",
                    snippet="一年期合同试用期上限一个月。",
                    channel="vector",
                    score=0.92,
                    query_unit_ids=tuple(unit.unit_id for unit in query_units),
                ),
            ),
            source_refs=("kb/law.md",),
            coverage_summary={"query_units": len(query_units), "sources": 1},
            quality_summary={"average_weighted_score": 0.9},
            missing_evidence_notes=(),
        )


class _RelatedOnlyRecoveryRetrievalPower:
    def __init__(self) -> None:
        self.last_queries = []

    def retrieve(self, query_units, *, top_k: int = 4) -> EvidenceBundle:
        del top_k
        self.last_queries = [unit.text for unit in query_units]
        return EvidenceBundle(
            query_unit_results=tuple(
                {
                    "unit_id": unit.unit_id,
                    "query": unit.text,
                    "origin": unit.origin,
                    "target_refs": list(unit.target_refs),
                }
                for unit in query_units
            ),
            merged_evidence_items=(
                EvidenceItem(
                    evidence_id="evidence_model_grounded",
                    source_path="notes/live_llm.md",
                    source_type="official_structured",
                    locator="section-1",
                    snippet="当前结论是不能直接断定这是模型问题，不是 prompt 问题。",
                    channel="vector",
                    score=0.95,
                    query_unit_ids=tuple(unit.unit_id for unit in query_units),
                ),
            ),
            source_refs=("notes/live_llm.md",),
            coverage_summary={"query_units": len(query_units), "sources": 1},
            quality_summary={"average_weighted_score": 0.95},
            missing_evidence_notes=(),
        )


class _CapturingChallengePower:
    def __init__(self) -> None:
        self.last_evidence_candidates = None
        self.last_kwargs = None

    def execute(self, **kwargs):
        self.last_kwargs = dict(kwargs)
        self.last_evidence_candidates = list(kwargs["evidence_candidates"])
        return ChallengeResult.from_review_evaluation(
            targets=(),
            evidence_assessment=EvidenceAssessmentResult(),
            evaluation=ReviewEvaluationResult(
                status="needs_clarification",
                review_findings=(),
                answer_constraints={"must_acknowledge_uncertainty": True},
            ),
        )


def _working_memory(*entries: WorkingMemoryEntry) -> SessionWorkingMemory:
    return SessionWorkingMemory(
        entries=list(entries),
        head=WorkingMemoryHead(active_entry_ids=[entry.entry_id for entry in entries]),
    )


def _make_plan(
    *,
    route: str,
    handling_mode: str,
    enabled_powers: tuple[str, ...] = (),
    use_planner: bool = False,
    decompose_query: bool = False,
    use_context: bool = False,
    action: str = "agent",
    should_ask_clarification_first: bool = False,
    missing_context_types: tuple[str, ...] = (),
) -> WorkflowPlan:
    trace = ControlTrace(
        main_intent="qa",
        modifiers=IntentModifiers(challenge=handling_mode == "challenge"),
        task_complexity="complex" if use_planner else "simple",
        task_shape="compare" if use_planner else "single_question",
        task_topology="parallel_queries" if decompose_query else "single",
        context_dependency="previous_answer" if use_context else "none",
        ambiguity_states=("history_dependent",) if use_context else (),
        missing_context_types=missing_context_types,
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    return WorkflowPlan(
        route=route,
        handling_mode=handling_mode,
        action=action,
        use_context=use_context,
        cite_sources=True,
        use_planner=use_planner,
        decompose_query=decompose_query,
        rewrite_query=use_context,
        should_ask_clarification_first=should_ask_clarification_first,
        trace=trace,
        enabled_powers=enabled_powers,  # type: ignore[arg-type]
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(
            need_planner=use_planner,
            need_query_decomposition=decompose_query,
            need_context_binding=use_context,
            ask_clarification_first=should_ask_clarification_first,
        ),
        notes=("test",),
    )


def test_orchestrated_runner_builds_plan_and_binding_bundle() -> None:
    runner = OrchestratedRouteRunner()
    plan = _make_plan(
        route="orchestrated",
        handling_mode="normal",
        enabled_powers=("context_binding_power", "planning_power", "decomposition_power"),
        use_planner=True,
        decompose_query=True,
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="比较A和B？再分别说明两者风险？",
        messages=[{"role": "user", "content": "比较A和B？再分别说明两者风险？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "比较A和B？",
                    "source_power": "workflow",
                    "refs": [],
                }
            ],
            "recent_power": "workflow",
            "recent_object_type": "question_object",
        },
    )

    payload = runner.run(plan, request)

    assert "binding" in payload.context_bundle
    assert payload.context_bundle["binding"]["binding_ambiguous"] is False
    assert payload.context_bundle["binding_summary"]
    assert "query_units" in payload.context_bundle
    assert payload.plan_bundle["ordered_steps"]
    assert payload.plan_bundle["goal"] == request.message
    assert payload.plan_bundle["task_shape"] == "compare"
    assert payload.plan_bundle["task_topology"] == "parallel_queries"
    assert payload.plan_bundle["planning_mode"] == "compare"
    assert payload.plan_bundle["query_units"][0]["unit_id"] == "q1"
    assert payload.plan_bundle["execution_checkpoints"]
    assert payload.plan_bundle["bound_target_refs"]
    assert payload.plan_bundle["fallback_used"] is False
    assert payload.plan_bundle["refined"] is False
    assert payload.plan_bundle["plan_summary"]["planning_mode"] == "compare"
    assert payload.plan_bundle["plan_summary"]["fallback_used"] is False
    assert payload.review_bundle["status"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["status_summary"] == "not_applicable"
    assert payload.review_bundle["review_mode"] == "not_applicable"
    assert payload.review_bundle["review_confidence"] == "not_applicable"
    assert payload.review_bundle["review_scope"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["review_mode"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["review_confidence"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["review_scope"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is False
    assert payload.context_bundle["candidate_count"] == 1
    assert payload.context_bundle["query_units"]


def test_qa_runner_challenge_without_candidates_requests_clarification() -> None:
    runner = QaRouteRunner()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "context_binding_power"),
    )
    request = RouteExecutionRequest(
        message="你刚才说的依据是什么？",
        messages=[{"role": "user", "content": "你刚才说的依据是什么？"}],
        context={"registry_entries": []},
    )

    payload = runner.run(plan, request)

    assert payload.status == "needs_clarification"
    assert payload.review_bundle["status"] == "needs_clarification"
    assert payload.review_bundle["review_summary"]["target_count"] == 0
    assert payload.review_bundle["review_summary"]["status_summary"] == "needs_clarification"
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["review_confidence"] == "low"
    assert payload.review_bundle["review_scope"] == "not_applicable"
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is False
    assert payload.review_bundle["targets"] == []
    assert payload.review_bundle["review_findings"] == []
    assert "binding_ambiguous" in payload.key_events
    assert "clarification_required" in payload.key_events


def test_qa_runner_challenge_with_evidence_candidates_returns_review_bundle() -> None:
    runner = QaRouteRunner()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "context_binding_power"),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="你刚才这个依据是什么？",
        messages=[{"role": "user", "content": "你刚才这个依据是什么？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "你刚才说的试用期依据是什么？",
                    "source_power": "workflow",
                    "refs": ["evidence_1"],
                },
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "劳动合同法第19条",
                    "source_power": "retrieval_power",
                    "refs": ["evidence_1"],
                },
            ],
            "recent_power": "workflow",
            "recent_object_type": "question_object",
        },
    )

    payload = runner.run(plan, request)
    exported = payload.to_dict()

    assert payload.status == "ready"
    assert payload.review_bundle["status"] == "success"
    assert exported["challenge_result_bundle"] == exported["review_bundle"]
    assert payload.review_bundle["evidence_assessment"]["sufficient"] is True
    assert payload.review_bundle["evidence_assessment"]["retrieve_if_needed"]["needed"] is False
    assert payload.context_bundle["binding"] is not None
    assert payload.context_bundle["binding_summary"]
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["review_confidence"] == "high"
    assert payload.review_bundle["review_scope"] == "single_target"
    assert isinstance(payload.review_bundle["targets"], list)
    assert isinstance(payload.review_bundle["review_findings"], list)
    assert payload.review_bundle["review_summary"]["matched_target_refs"] == ["question_1"]
    assert payload.review_bundle["review_summary"]["status_summary"] == "success"
    assert payload.review_bundle["review_summary"]["used_existing_evidence"] is True
    assert payload.review_bundle["review_summary"]["retrieve_if_needed_needed"] is False
    assert payload.context_bundle["binding"]["binding_snapshot"]["query_style"] == "challenge"
    assert "question_1" in payload.context_bundle["binding"]["resolved_target_ids"]
    assert "binding_applied" in payload.key_events


def test_qa_runner_challenge_supports_multi_target_partial_review_bundle() -> None:
    runner = QaRouteRunner()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "context_binding_power"),
    )
    request = RouteExecutionRequest(
        message="前两个结论的依据都对吗？",
        messages=[{"role": "user", "content": "前两个结论的依据都对吗？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "劳动合同法第19条",
                    "source_power": "retrieval_power",
                    "refs": ["evidence_1"],
                },
            ],
            "working_memory": _working_memory(
                WorkingMemoryEntry(
                    entry_id="wm_answer_1",
                    entry_type="answer_unit",
                    turn_id="turn_1",
                    source_kind="answer",
                    source_ref="turn_1:answer:1",
                    content="第一点：第一个结论的依据是什么？",
                    structured_payload={"unit_index": 1, "refs": ["evidence_1"]},
                    confidence="high",
                ),
                WorkingMemoryEntry(
                    entry_id="wm_answer_2",
                    entry_type="answer_unit",
                    turn_id="turn_1",
                    source_kind="answer",
                    source_ref="turn_1:answer:2",
                    content="第二点：第二个结论的依据是什么？",
                    structured_payload={"unit_index": 2, "refs": ["evidence_2"]},
                    confidence="high",
                ),
            ),
        },
    )

    payload = runner.run(plan, request)
    exported = payload.to_dict()

    assert payload.status == "needs_clarification"
    assert payload.review_bundle["status"] == "needs_clarification"
    assert exported["challenge_result_bundle"] == exported["review_bundle"]
    assert payload.review_bundle["evidence_assessment"]["sufficient"] is False
    assert payload.review_bundle["review_findings"] == []
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["review_confidence"] == "low"
    assert payload.review_bundle["review_scope"] == "multi_target"
    assert len(payload.review_bundle["targets"]) == 2
    assert [item["object_id"] for item in payload.review_bundle["targets"]] == ["wm_answer_1", "wm_answer_2"]
    assert payload.review_bundle["review_summary"]["unsupported_target_refs"] == []
    assert payload.review_bundle["review_summary"]["needs_more_evidence_targets"] == []
    assert payload.review_bundle["review_summary"]["status_summary"] == "needs_clarification"
    assert payload.review_bundle["review_summary"]["used_existing_evidence"] is True
    assert payload.review_bundle["review_summary"]["retrieve_if_needed_needed"] is False
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is False
    assert "clarification_required" in payload.key_events


def test_qa_runner_challenge_can_resolve_missing_targets_via_follow_up_retrieval() -> None:
    runner = QaRouteRunner()
    runner.retrieval_power = _FakeRetrievalPower()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "retrieval_power", "context_binding_power"),
    )
    request = RouteExecutionRequest(
        message="前两个结论的依据都对吗？",
        messages=[{"role": "user", "content": "前两个结论的依据都对吗？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "劳动合同法第19条",
                    "source_power": "retrieval_power",
                    "refs": ["evidence_1"],
                },
            ],
            "working_memory": _working_memory(
                WorkingMemoryEntry(
                    entry_id="wm_answer_1",
                    entry_type="answer_unit",
                    turn_id="turn_1",
                    source_kind="answer",
                    source_ref="turn_1:answer:1",
                    content="第一点：第一个结论的依据是什么？",
                    structured_payload={"unit_index": 1, "refs": ["evidence_1"]},
                    confidence="high",
                ),
                WorkingMemoryEntry(
                    entry_id="wm_answer_2",
                    entry_type="answer_unit",
                    turn_id="turn_1",
                    source_kind="answer",
                    source_ref="turn_1:answer:2",
                    content="第二点：第二个结论的依据是什么？",
                    structured_payload={"unit_index": 2, "refs": ["evidence_2"]},
                    confidence="high",
                ),
            ),
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "needs_clarification"
    assert payload.review_bundle["status"] == "needs_clarification"
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["review_confidence"] == "low"
    assert payload.review_bundle["review_scope"] == "multi_target"
    assert len(payload.review_bundle["targets"]) == 2
    assert [item["object_id"] for item in payload.review_bundle["targets"]] == ["wm_answer_1", "wm_answer_2"]
    assert payload.review_bundle["review_summary"]["matched_target_count"] == 0
    assert payload.review_bundle["review_summary"]["unsupported_target_refs"] == []
    assert payload.review_bundle["review_summary"]["used_existing_evidence"] is True
    assert payload.review_bundle["review_summary"]["retrieve_if_needed_needed"] is False
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is False
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_sources"] == []
    assert runner.retrieval_power.last_query_units == []
    assert "clarification_required" in payload.key_events


def test_qa_runner_real_challenge_case_related_only_existing_evidence_uses_targeted_retrieval() -> None:
    runner = QaRouteRunner()
    runner.retrieval_power = _RelatedOnlyRecoveryRetrievalPower()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "retrieval_power", "context_binding_power"),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="那是模型的问题, 不是我们prompt问题?",
        messages=[
            {"role": "user", "content": "现在回顾一下 live llm resolution 的归因边界。"},
            {
                "role": "assistant",
                "content": (
                    "第一点：当前结论是不能直接断定这是模型问题，不是 prompt 问题。"
                    "第二点：当前结论是 live llm 运行面同时包含模型输出、prompt、parser 和连通性风险。"
                ),
            },
            {"role": "user", "content": "那是模型的问题, 不是我们prompt问题?"},
        ],
        context={
            "recent_messages": [
                {"role": "user", "content": "现在回顾一下 live llm resolution 的归因边界。"},
                {
                    "role": "assistant",
                    "content": (
                        "第一点：当前结论是不能直接断定这是模型问题，不是 prompt 问题。"
                        "第二点：当前结论是 live llm 运行面同时包含模型输出、prompt、parser 和连通性风险。"
                    ),
                },
            ],
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "当前结论是不能直接断定这是模型问题，不是 prompt 问题。",
                    "source_power": "workflow",
                    "refs": ["evidence_model_grounded"],
                },
                {
                    "object_id": "evidence_related",
                    "object_type": "evidence_ref",
                    "content": "当前结论是不能直接断定这是模型问题，不是 prompt 问题，但当前仍不能单点归因。",
                    "source_power": "retrieval_power",
                    "source_type": "official_structured",
                    "channel": "vector",
                    "refs": [],
                },
            ],
            "recent_power": "workflow",
            "recent_object_type": "question_object",
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert payload.review_bundle["status"] == "success"
    assert payload.review_bundle["evidence_assessment"]["follow_up_retrieval"]["attempted"] is True
    assert payload.review_bundle["review_summary"]["used_existing_evidence"] is True
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is True
    assert payload.review_bundle["review_summary"]["retrieve_if_needed_needed"] is False
    assert "follow_up_retrieval_attempted" in payload.key_events
    assert "follow_up_retrieval_improved" in payload.key_events
    assert runner.retrieval_power.last_queries
    assert len(runner.retrieval_power.last_queries) == 1
    assert "不能直接断定这是模型问题" in runner.retrieval_power.last_queries[0]
    assert "live llm 运行面同时包含模型输出" not in runner.retrieval_power.last_queries[0]


def test_qa_runner_real_challenge_case_related_only_existing_evidence_without_retrieval_stays_insufficient() -> None:
    runner = QaRouteRunner()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "context_binding_power"),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="那是模型的问题, 不是我们prompt问题?",
        messages=[
            {"role": "user", "content": "现在回顾一下 live llm resolution 的归因边界。"},
            {
                "role": "assistant",
                "content": (
                    "第一点：当前结论是不能直接断定这是模型问题，不是 prompt 问题。"
                    "第二点：当前结论是 live llm 运行面同时包含模型输出、prompt、parser 和连通性风险。"
                ),
            },
            {"role": "user", "content": "那是模型的问题, 不是我们prompt问题?"},
        ],
        context={
            "recent_messages": [
                {"role": "user", "content": "现在回顾一下 live llm resolution 的归因边界。"},
                {
                    "role": "assistant",
                    "content": (
                        "第一点：当前结论是不能直接断定这是模型问题，不是 prompt 问题。"
                        "第二点：当前结论是 live llm 运行面同时包含模型输出、prompt、parser 和连通性风险。"
                    ),
                },
            ],
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "当前结论是不能直接断定这是模型问题，不是 prompt 问题。",
                    "source_power": "workflow",
                    "refs": ["evidence_model_grounded"],
                },
                {
                    "object_id": "evidence_related",
                    "object_type": "evidence_ref",
                    "content": "当前结论是不能直接断定这是模型问题，不是 prompt 问题，但当前仍不能单点归因。",
                    "source_power": "retrieval_power",
                    "source_type": "official_structured",
                    "channel": "vector",
                    "refs": [],
                },
            ],
            "recent_power": "workflow",
            "recent_object_type": "question_object",
        },
    )

    payload = runner.run(plan, request)

    assert payload.review_bundle["status"] == "insufficient_evidence"
    assert payload.review_bundle["evidence_assessment"]["retrieve_if_needed"]["needed"] is True
    assert payload.review_bundle["evidence_assessment"]["retrieve_if_needed"]["reason"] == "related_evidence_not_grounded"
    assert payload.review_bundle["review_summary"]["follow_up_retrieval_attempted"] is False
    assert "insufficient_evidence" in payload.key_events


def test_qa_runner_passes_typed_evidence_candidates_into_challenge_power() -> None:
    runner = QaRouteRunner()
    runner.challenge_power = _CapturingChallengePower()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power",),
    )
    request = RouteExecutionRequest(
        message="你刚才这个依据是什么？",
        messages=[{"role": "user", "content": "你刚才这个依据是什么？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "你刚才这个依据是什么？",
                    "source_power": "workflow",
                    "refs": ["evidence_1"],
                },
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "劳动合同法第19条",
                    "source_power": "retrieval_power",
                    "refs": ["evidence_1"],
                },
            ],
        },
    )

    runner.run(plan, request)

    assert isinstance(runner.challenge_power.last_evidence_candidates[0], EvidenceRefCandidate)


def test_qa_runner_hydrates_memory_anchor_context_when_summary_is_not_enough(tmp_path) -> None:
    runner = QaRouteRunner()
    session_manager = SessionManager(tmp_path / "storage")
    session = session_manager.create_session("law", DEFAULT_AGENT, "user_a")
    session_manager.append_entry(
        "law",
        DEFAULT_AGENT,
        TranscriptEntry(
            id="entry_1",
            session_id=session.id,
            group_id="law",
            timestamp=1,
            role="assistant",
            entry_type="normal",
            content="之前那个案例里，结论是试用期上限要看合同期限。",
        ),
    )
    anchor = MemoryAnchorBuilder().build(
        MemoryEntry(
            content="之前讨论过一个试用期案例。",
            source="users/default/groups/law/daily_logs/2026-05-24.jsonl",
            group_id="law",
            timestamp=datetime.now(),
            memory_type="daily_log",
            source_session_id=session.id,
        )
    )
    plan = _make_plan(
        route="qa",
        handling_mode="normal",
        enabled_powers=("context_binding_power",),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="那个案例的结论是什么？",
        messages=[{"role": "user", "content": "那个案例的结论是什么？"}],
        context={
            "session_manager": session_manager,
            "active_group_id": "law",
            "agent_id": DEFAULT_AGENT,
            "memory_anchors": [anchor.to_dict()],
            "memory_anchor_summary_sufficient": False,
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert request.context["memory_anchor_hydrated"] is True
    assert request.context["hydrated_memory_entry_count"] == 1
    assert payload.context_bundle["memory_anchor_count"] == 1
    assert payload.context_bundle["hydrated_memory_entry_count"] == 1
    assert payload.context_bundle["memory_hydrated"] is True
    assert payload.context_bundle["candidate_count"] == 1
    assert "memory_anchor_hydrated" in payload.key_events
    assert payload.context_bundle["binding"]["binding_snapshot"]["candidate_source_counts"]["memory_anchor_hydrate"] == 1
    assert payload.context_bundle["binding"]["relevant_set"][0]["object_type"] in {"answer_unit", "memory_anchor"}


def test_qa_runner_skips_memory_anchor_hydration_when_summary_is_already_enough(tmp_path) -> None:
    runner = QaRouteRunner()
    session_manager = SessionManager(tmp_path / "storage")
    session = session_manager.create_session("law", DEFAULT_AGENT, "user_a")
    session_manager.append_entry(
        "law",
        DEFAULT_AGENT,
        TranscriptEntry(
            id="entry_1",
            session_id=session.id,
            group_id="law",
            timestamp=1,
            role="assistant",
            entry_type="normal",
            content="这个上下文不该被 hydrate 进去。",
        ),
    )
    anchor = MemoryAnchorBuilder().build(
        MemoryEntry(
            content="之前讨论过一个试用期案例。",
            source="users/default/groups/law/daily_logs/2026-05-24.jsonl",
            group_id="law",
            timestamp=datetime.now(),
            memory_type="daily_log",
            source_session_id=session.id,
        )
    )
    plan = _make_plan(
        route="qa",
        handling_mode="normal",
        enabled_powers=("context_binding_power",),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="那个案例的结论是什么？",
        messages=[{"role": "user", "content": "那个案例的结论是什么？"}],
        context={
            "session_manager": session_manager,
            "active_group_id": "law",
            "agent_id": DEFAULT_AGENT,
            "memory_anchors": [anchor.to_dict()],
            "memory_anchor_summary_sufficient": True,
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert request.context.get("memory_anchor_hydrated") is None
    assert payload.context_bundle["memory_anchor_count"] == 1
    assert payload.context_bundle["hydrated_memory_entry_count"] == 0
    assert payload.context_bundle["memory_hydrated"] is False
    assert payload.context_bundle["candidate_count"] == 0
    assert "memory_anchor_hydrated" not in payload.key_events
    assert "memory_anchor_hydrate" not in payload.context_bundle["binding"]["binding_snapshot"]["candidate_source_counts"]


def test_orchestrated_runner_passes_binding_result_into_challenge_power() -> None:
    runner = OrchestratedRouteRunner()
    runner.challenge_power = _CapturingChallengePower()
    plan = _make_plan(
        route="orchestrated",
        handling_mode="challenge",
        enabled_powers=("challenge_power", "context_binding_power"),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="这个依据是什么？",
        messages=[{"role": "user", "content": "这个依据是什么？"}],
        context={
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "你刚才这个依据是什么？",
                    "source_power": "workflow",
                    "refs": ["evidence_1"],
                },
            ],
            "recent_power": "workflow",
            "recent_object_type": "question_object",
        },
    )

    runner.run(plan, request)

    assert runner.challenge_power.last_kwargs is not None
    assert runner.challenge_power.last_kwargs["binding_result"] is not None


def test_orchestrated_runner_uses_staged_planning_mode_for_staged_tasks() -> None:
    runner = OrchestratedRouteRunner()
    trace = ControlTrace(
        main_intent="qa",
        modifiers=IntentModifiers(),
        task_complexity="complex",
        task_shape="verify",
        task_topology="staged",
        context_dependency="none",
        ambiguity_states=(),
        missing_context_types=(),
        decision_strength="high",
        decision_source="rule",
        decision_reason="test",
    )
    plan = WorkflowPlan(
        route="orchestrated",
        handling_mode="normal",
        action="agent",
        use_context=False,
        cite_sources=True,
        use_planner=True,
        decompose_query=False,
        rewrite_query=False,
        should_ask_clarification_first=False,
        trace=trace,
        enabled_powers=("planning_power",),
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(need_planner=True),
        notes=("test",),
    )
    request = RouteExecutionRequest(
        message="先核验法规前提，再给出最终结论。",
        messages=[{"role": "user", "content": "先核验法规前提，再给出最终结论。"}],
        context={},
    )

    payload = runner.run(plan, request)

    assert payload.plan_bundle["planning_mode"] == "staged"
    assert payload.plan_bundle["fallback_used"] is False
    assert payload.plan_bundle["plan_summary"]["planning_mode"] == "staged"
    titles = [step["title"] for step in payload.plan_bundle["ordered_steps"]]
    assert "Preserve stage dependencies" in titles


def test_execution_payload_keeps_string_route_and_handling_mode_contract() -> None:
    runner = QaRouteRunner()
    plan = _make_plan(
        route="qa",
        handling_mode="challenge",
        enabled_powers=("challenge_power",),
    )
    request = RouteExecutionRequest(
        message="你刚才这个依据是什么？",
        messages=[{"role": "user", "content": "你刚才这个依据是什么？"}],
        context={"registry_entries": []},
    )

    payload = runner.run(plan, request).to_dict()

    assert payload["route"] == "qa"
    assert isinstance(payload["route"], str)
    assert payload["handling_mode"] == "challenge"
    assert isinstance(payload["handling_mode"], str)


def test_reject_runner_sets_policy_reject_summary_and_constraints() -> None:
    runner = RejectRouteRunner()
    plan = _make_plan(
        route="reject",
        handling_mode="unsupported",
        action="reject",
    )
    request = RouteExecutionRequest(
        message="帮我执行不支持的操作",
        messages=[{"role": "user", "content": "帮我执行不支持的操作"}],
        context={},
    )

    payload = runner.run(plan, request)

    assert payload.status == "rejected"
    assert payload.context_bundle["reject_summary"]["reason_code"] == "policy_reject"
    assert payload.answer_constraints["allow_substantive_answer"] is False
    assert payload.answer_constraints["must_explain_boundary"] is True
    assert payload.answer_constraints["must_offer_safe_alternative"] is True
    assert payload.key_events == ("policy_reject",)
    assert payload.enabled_powers == ()


def test_reject_runner_sets_capability_reject_summary() -> None:
    runner = RejectRouteRunner()
    plan = _make_plan(
        route="reject",
        handling_mode="normal",
        action="reject",
    )
    request = RouteExecutionRequest(
        message="这个请求超出能力边界",
        messages=[{"role": "user", "content": "这个请求超出能力边界"}],
        context={},
    )

    payload = runner.run(plan, request)

    assert payload.status == "rejected"
    assert payload.context_bundle["reject_summary"]["reason_code"] == "capability_reject"
    assert payload.key_events == ("capability_reject",)
    assert payload.answer_constraints["must_ask_clarification_first"] is False


def test_reject_runner_sets_clarification_first_reject_when_requested() -> None:
    runner = RejectRouteRunner()
    plan = _make_plan(
        route="reject",
        handling_mode="clarify",
        action="respond",
        should_ask_clarification_first=True,
        missing_context_types=("missing_history_target",),
    )
    request = RouteExecutionRequest(
        message="你说的是哪个案例？",
        messages=[{"role": "user", "content": "你说的是哪个案例？"}],
        context={},
    )

    payload = runner.run(plan, request)

    assert payload.status == "needs_clarification"
    assert payload.context_bundle["reject_summary"]["reason_code"] == "clarification_first_reject"
    assert payload.answer_constraints["must_ask_clarification_first"] is True
    assert payload.key_events == ("clarification_required",)


def test_chat_runner_executes_optional_context_binding_without_heavy_outputs() -> None:
    runner = ChatRouteRunner()
    plan = _make_plan(
        route="chat",
        handling_mode="normal",
        action="respond",
        enabled_powers=("context_binding_power",),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="那上面那个呢",
        messages=[{"role": "user", "content": "那上面那个呢"}],
        context={
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "上一个问题是什么？",
                    "source_power": "workflow",
                    "refs": [],
                    "confidence": "high",
                }
            ],
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "ready"
    assert payload.context_bundle["binding"] is not None
    assert payload.context_bundle["binding_summary"] != "not_applicable"
    assert payload.context_bundle["candidate_count"] == 1
    assert payload.key_events == ("binding_applied",)
    assert payload.review_bundle["status"] == "not_applicable"
    assert payload.plan_bundle["planning_mode"] == "not_applicable"
    assert payload.evidence_bundle is None


def test_chat_runner_returns_needs_clarification_for_ambiguous_binding() -> None:
    runner = ChatRouteRunner()
    plan = _make_plan(
        route="chat",
        handling_mode="normal",
        action="respond",
        enabled_powers=("context_binding_power",),
        use_context=True,
    )
    request = RouteExecutionRequest(
        message="那个呢",
        messages=[{"role": "user", "content": "那个呢"}],
        context={
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "第一个问题",
                    "source_power": "workflow",
                    "refs": [],
                    "confidence": "high",
                },
                {
                    "object_id": "question_2",
                    "object_type": "question_object",
                    "content": "第二个问题",
                    "source_power": "workflow",
                    "refs": [],
                    "confidence": "high",
                },
            ],
        },
    )

    payload = runner.run(plan, request)

    assert payload.status == "needs_clarification"
    assert payload.context_bundle["binding"] is not None
    assert payload.context_bundle["binding"]["needs_clarification"] is True
    assert "clarification_required" in payload.key_events
    assert "binding_ambiguous" in payload.key_events
