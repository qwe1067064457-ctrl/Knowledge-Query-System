from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

import pytest

from config import get_settings, runtime_config
from graph.prompt_builders.answer_prompt_assembler import assemble_answer_messages
from graph.prompt_builders.workflow_prompt_projector import (
    build_answer_behavior_rules_from_workflow,
    build_answer_result_projection_rules_from_workflow,
)
from intent.schema.intent_types import ControlTrace, IntentModifiers
from llm.model_factory import build_chat_model
from llm.output_sanitizer import sanitize_model_text
from memory_system.session_working_memory.writer import SessionWorkingMemoryWriter
from workflow.runners.base import RouteExecutionRequest
from workflow.runners.qa_runner import QaRouteRunner
from workflow.types import WorkflowPlan, WorkflowPolicyFlags


def _stringify_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content or "")


def _has_live_llm_key() -> bool:
    return bool(get_settings().llm_api_key)


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "backend"


def _invoke_live_prompt_or_skip(messages: list[dict[str, str]]) -> str:
    def _invoke() -> str:
        response = build_chat_model().invoke(messages)
        return sanitize_model_text(_stringify_content(getattr(response, "content", "")))

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_invoke)
            return future.result(timeout=90)
    except FutureTimeoutError as exc:  # pragma: no cover - external runtime branch
        pytest.skip(f"live answer model timed out: {exc}")
    except Exception as exc:  # pragma: no cover - external runtime branch
        pytest.skip(f"live answer model unavailable: {exc}")


def _live_llm_call(prompt: str) -> str:
    return _invoke_live_prompt_or_skip([{"role": "user", "content": prompt}])


def _make_plan(
    *,
    handling_mode: str = "normal",
    enabled_powers: tuple[str, ...] = (),
    use_context: bool = False,
) -> WorkflowPlan:
    trace = ControlTrace(
        main_intent="qa",
        modifiers=IntentModifiers(challenge=handling_mode == "challenge"),
        task_complexity="simple",
        task_shape="single_question",
        task_topology="single",
        context_dependency="previous_answer" if use_context else "none",
        ambiguity_states=("history_dependent",) if use_context else (),
        missing_context_types=(),
        decision_strength="high",
        decision_source="rule",
        decision_reason="live_e2e_smoke",
    )
    return WorkflowPlan(
        route="qa",
        handling_mode=handling_mode,
        action="respond",
        use_context=use_context,
        cite_sources=True,
        use_planner=False,
        decompose_query=False,
        rewrite_query=use_context,
        should_ask_clarification_first=False,
        trace=trace,
        enabled_powers=enabled_powers,  # type: ignore[arg-type]
        knowledge_scope_status="resolved",
        policy_flags=WorkflowPolicyFlags(
            need_context_binding=use_context,
        ),
        notes=("qa_runner_e2e_live_smoke",),
    )


def _build_working_memory(
    *,
    turn_id: str,
    user_query: str,
    answer_text: str,
    current_goal: str,
    review_result: dict[str, str] | None = None,
):
    writer = SessionWorkingMemoryWriter()
    return writer.build_entries_from_turn(
        turn_id=turn_id,
        user_query=user_query,
        answer_text=answer_text,
        current_goal=current_goal,
        review_result=review_result,
    )


def _run_qa_and_answer(
    *,
    plan: WorkflowPlan,
    message: str,
    history: list[dict[str, str]],
    context: dict[str, object],
):
    runner = QaRouteRunner()
    request = RouteExecutionRequest(
        message=message,
        messages=history,
        is_knowledge_query=False,
        context=context,
    )
    payload = runner.run(plan, request)
    workflow_instructions = list(payload.instructions) or build_answer_behavior_rules_from_workflow(plan)
    workflow_instructions.extend(build_answer_result_projection_rules_from_workflow(payload))
    answer_messages = assemble_answer_messages(
        _backend_dir(),
        history,
        rag_mode=runtime_config.get_rag_mode(),
        extra_instructions=workflow_instructions,
    )
    answer_text = _invoke_live_prompt_or_skip(answer_messages)
    return payload, answer_text


pytestmark = pytest.mark.skipif(
    not _has_live_llm_key(),
    reason="live qa-runner e2e smoke requires configured LLM_API_KEY",
)


def test_live_qa_runner_e2e_followup_with_answer_model() -> None:
    previous_user = "所以现在模型的调通了,只是返回结果不稳定。"
    previous_answer = (
        "第一点：当前结论是模型调用链已经调通。"
        "第二点：当前结论是 live 返回结果还没有稳定落成可消费 resolution。"
        "第三点：当前结论是现在 build_chat_model 里调的是 MiniMax。"
    )
    current_query = "那我们现在怎么做? 就是还要去调大模型吗?现在build model里面我们调的是MiniMax了。"
    history = [
        {"role": "user", "content": previous_user},
        {"role": "assistant", "content": previous_answer},
        {"role": "user", "content": current_query},
    ]
    memory_entries = _build_working_memory(
        turn_id="turn_live_e2e_followup",
        user_query=previous_user,
        answer_text=previous_answer,
        current_goal="确认 live llm 当前状态和下一步策略",
        review_result={"status": "active", "summary": "当前仍需看 QA Runner 整体是否可接受。"},
    )
    plan = _make_plan(
        handling_mode="normal",
        enabled_powers=("context_binding_power",),
        use_context=True,
    )

    payload, answer_text = _run_qa_and_answer(
        plan=plan,
        message=current_query,
        history=history,
        context={
            "working_memory": {"entries": [entry.to_dict() for entry in memory_entries], "head": {"active_entry_ids": [entry.entry_id for entry in memory_entries]}},
            "recent_messages": history[-3:],
            "registry_entries": [],
            "bound_query_llm_call": _live_llm_call,
            "base_dir": _backend_dir(),
        },
    )

    assert payload.route == "qa"
    assert payload.context_bundle["binding"] is not None
    assert payload.context_bundle["binding_summary"]
    assert payload.status in {"ready", "needs_clarification"}
    assert answer_text
    assert "<think>" not in answer_text.lower()


def test_live_qa_runner_e2e_clarification_path_with_answer_model() -> None:
    previous_user = "解释一下 relevant set 在不同场景里的角色。"
    previous_answer = (
        "第一点：进入 Context Binding 以后，核心中间产物就是 relevant set。"
        "第二点：follow_up、challenge、multi_target 会消费 relevant set。"
        "第三点：规则层负责 guardrail 和 prefilter。"
    )
    current_query = "所以,不管是哪种场景,我们都需要有一个relevant set,后面是不是要真正的消费这个relevant的set?"
    history = [
        {"role": "user", "content": previous_user},
        {"role": "assistant", "content": previous_answer},
        {"role": "user", "content": current_query},
    ]
    memory_entries = _build_working_memory(
        turn_id="turn_live_e2e_clarify",
        user_query=previous_user,
        answer_text=previous_answer,
        current_goal="说明 relevant set 的中间层作用",
        review_result={"status": "active", "summary": "当前仍需观察 multi_target 对 都 的敏感度。"},
    )
    plan = _make_plan(
        handling_mode="normal",
        enabled_powers=("context_binding_power",),
        use_context=True,
    )

    payload, answer_text = _run_qa_and_answer(
        plan=plan,
        message=current_query,
        history=history,
        context={
            "working_memory": {"entries": [entry.to_dict() for entry in memory_entries], "head": {"active_entry_ids": [entry.entry_id for entry in memory_entries]}},
            "recent_messages": history[-3:],
            "registry_entries": [],
            "bound_query_llm_call": _live_llm_call,
            "base_dir": _backend_dir(),
        },
    )

    assert payload.route == "qa"
    assert payload.context_bundle["binding"] is not None
    assert payload.context_bundle["binding"]["fallback_type"] in {"needs_clarification", "retrieve_on_raw_query", None}
    assert answer_text
    assert "<think>" not in answer_text.lower()


def test_live_qa_runner_e2e_challenge_with_answer_model() -> None:
    previous_user = "现在回顾一下 live llm resolution 的归因边界。"
    previous_answer = (
        "第一点：当前结论是不能直接断定这是模型问题，不是 prompt 问题。"
        "第二点：当前结论是 live llm 运行面同时包含模型输出、prompt、parser 和连通性风险。"
        "第三点：当前结论是 QA Runner 下一步更适合看整体是否可接受。"
    )
    current_query = "那是模型的问题, 不是我们prompt问题?"
    history = [
        {"role": "user", "content": previous_user},
        {"role": "assistant", "content": previous_answer},
        {"role": "user", "content": current_query},
    ]
    memory_entries = _build_working_memory(
        turn_id="turn_live_e2e_challenge",
        user_query=previous_user,
        answer_text=previous_answer,
        current_goal="澄清模型问题与 prompt 问题的归因边界",
        review_result={"status": "active", "summary": "当前更像 live 运行面不稳定，不是单点归因。"},
    )
    plan = _make_plan(
        handling_mode="challenge",
        enabled_powers=("context_binding_power", "challenge_power"),
        use_context=True,
    )

    payload, answer_text = _run_qa_and_answer(
        plan=plan,
        message=current_query,
        history=history,
        context={
            "working_memory": {"entries": [entry.to_dict() for entry in memory_entries], "head": {"active_entry_ids": [entry.entry_id for entry in memory_entries]}},
            "recent_messages": history[-3:],
            "registry_entries": [
                {
                    "object_id": "question_1",
                    "object_type": "question_object",
                    "content": "当前结论是不能直接断定这是模型问题，不是 prompt 问题。",
                    "source_power": "workflow",
                    "refs": ["evidence_1"],
                },
                {
                    "object_id": "evidence_1",
                    "object_type": "evidence_ref",
                    "content": "live llm 场景里出现过 llm_resolution_failed 和 APIConnectionError。",
                    "source_power": "retrieval_power",
                    "refs": ["evidence_1"],
                },
            ],
            "bound_query_llm_call": _live_llm_call,
            "base_dir": _backend_dir(),
        },
    )

    assert payload.route == "qa"
    assert payload.review_bundle["review_mode"] == "challenge_review"
    assert payload.review_bundle["status"] in {"success", "partial_success", "needs_clarification", "insufficient_evidence"}
    assert answer_text
    assert "<think>" not in answer_text.lower()
