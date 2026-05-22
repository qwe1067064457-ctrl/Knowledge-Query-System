from __future__ import annotations

import json
import re
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

try:
    from langchain_deepseek import ChatDeepSeek
except ImportError:  # pragma: no cover - optional dependency at runtime
    ChatDeepSeek = None

from config import get_settings, runtime_config
from graph.memory_indexer import memory_indexer
from graph.prompt_builder import build_system_prompt
from intent import classify_intent
from intent.loaders import load_group_intent_rule_assets
from knowledge_retrieval import knowledge_orchestrator
from memory_system import MemorySystem
from tools import get_all_tools
from workflow import WorkflowDispatcher, WorkflowPlan, build_workflow_plan
from workflow.powers.retrieval_power import RetrievalPower
from workflow.runners.base import RouteExecutionRequest

# 导入新的 context 模块
from context.registry_types import ContextRegistryEntry
from context.session_manager import SessionManager
from context.context_manager import ContextManager
from context.legacy_adapter import DEFAULT_AGENT, DEFAULT_GROUP, LegacySessionManagerAdapter

KNOWLEDGE_SKILL_PATTERNS = (
    re.compile(r"知识库"),
    re.compile(r"\bknowledge\b", re.IGNORECASE),
    re.compile(r"根据.+?(知识库|文档|资料)"),
    re.compile(r"(查|检索).+?(文档|资料|报告|白皮书)"),
    re.compile(r"\.(pdf|xlsx|xls|json)\b", re.IGNORECASE),
)


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content or "")


class AgentManager:
    def __init__(self) -> None:
        self.base_dir: Path | None = None
        self.raw_session_manager: SessionManager | None = None
        self.session_manager: LegacySessionManagerAdapter | None = None
        self.memory_system: MemorySystem | None = None
        self.context_manager: ContextManager | None = None
        self.workflow_dispatcher = WorkflowDispatcher()
        self.retrieval_power = RetrievalPower()
        self.tools = []

    def initialize(self, base_dir: Path) -> None:
        self.base_dir = base_dir

        # 初始化新的 context 模块
        self.raw_session_manager = SessionManager(base_dir / "storage")
        self.memory_system = MemorySystem(base_dir / "storage")
        self.context_manager = ContextManager(self.raw_session_manager, self.memory_system)
        # 设置 LLM 调用用于 compaction
        self.context_manager.set_llm_call(self._llm_text_call)

        # 初始化 legacy 适配器（保持向后兼容）
        self.session_manager = LegacySessionManagerAdapter(self.raw_session_manager)
        self.session_manager.configure_legacy_paths(base_dir)

        self.tools = get_all_tools(base_dir)
        knowledge_orchestrator.configure(base_dir, self._build_chat_model)

    def _build_chat_model(self):
        settings = get_settings()

        if settings.llm_provider == "deepseek":
            if ChatDeepSeek is None:
                raise RuntimeError("langchain-deepseek is not installed")
            if not settings.llm_api_key:
                raise RuntimeError("Missing API key for provider deepseek")
            return ChatDeepSeek(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                temperature=0,
            )

        if not settings.llm_api_key:
            raise RuntimeError(f"Missing API key for provider {settings.llm_provider}")

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0,
        )

    async def _llm_text_call(self, prompt: str) -> str:
        response = await self._build_chat_model().ainvoke(
            [{"role": "user", "content": prompt}]
        )
        return _stringify_content(getattr(response, "content", "")).strip()

    def _build_agent(
        self,
        extra_instructions: list[str] | None = None,
        tools_override: list[Any] | None = None,
    ):
        if self.base_dir is None:
            raise RuntimeError("AgentManager is not initialized")

        system_prompt = build_system_prompt(self.base_dir, runtime_config.get_rag_mode())
        if extra_instructions:
            system_prompt = f"{system_prompt}\n\n" + "\n\n".join(extra_instructions)
        return create_agent(
            model=self._build_chat_model(),
            tools=self.tools if tools_override is None else tools_override,
            system_prompt=system_prompt,
        )

    def _is_knowledge_query(self, message: str) -> bool:
        return any(pattern.search(message) for pattern in KNOWLEDGE_SKILL_PATTERNS)

    def _build_messages(self, history: list[dict[str, Any]]) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for item in history:
            role = item.get("role")
            if role not in {"system", "user", "assistant"}:
                continue
            messages.append({"role": role, "content": str(item.get("content", ""))})
        return messages

    def _insert_before_latest_user(
        self,
        messages: list[dict[str, str]],
        context_message: dict[str, str],
    ) -> list[dict[str, str]]:
        insert_at = len(messages)
        for index in range(len(messages) - 1, -1, -1):
            if messages[index].get("role") == "user":
                insert_at = index
                break
        return messages[:insert_at] + [context_message] + messages[insert_at:]

    async def _prepare_messages_for_request(
        self,
        session_id: str | None,
        message: str,
        history: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        current_user = {"role": "user", "content": message}
        if self.context_manager is None:
            messages = self._build_messages(history)
            messages.append(current_user)
            return messages

        has_new_transcript = False
        if session_id and self.raw_session_manager is not None:
            has_new_transcript = bool(
                self.raw_session_manager.get_transcript(
                    DEFAULT_GROUP,
                    DEFAULT_AGENT,
                    session_id,
                    limit=1,
                    include_compacted=True,
                )
            )

        if session_id and has_new_transcript:
            prepared = await self.context_manager.prepare(
                DEFAULT_GROUP,
                DEFAULT_AGENT,
                session_id,
                extra_messages=[current_user],
                query=message,
            )
        else:
            messages = self._build_messages(history)
            messages.append(current_user)
            prepared = await self.context_manager.prepare_messages(
                DEFAULT_GROUP,
                DEFAULT_AGENT,
                messages,
                query=message,
            )

        return self._build_messages(prepared["messages"])

    def _format_retrieval_context(self, results: list[dict[str, Any]]) -> str:
        lines = ["[RAG retrieved memory context]"]
        for idx, item in enumerate(results, start=1):
            text = str(item.get("text", "")).strip()
            source = str(item.get("source", "memory/MEMORY.md"))
            lines.append(f"{idx}. Source: {source}\n{text}")
        return "\n\n".join(lines)

    def _format_memory_retrieval_step(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "kind": "memory",
            "stage": "memory",
            "title": f"Memory 检索到 {len(results)} 条片段",
            "message": "已将 Memory 召回结果注入当前请求上下文。",
            "results": [
                {
                    "source_path": str(item.get("source", "memory/MEMORY.md")),
                    "source_type": "memory",
                    "locator": "memory",
                    "snippet": str(item.get("text", "")).strip(),
                    "channel": "memory",
                    "score": float(item.get("score", 0.0) or 0.0),
                    "parent_id": None,
                }
                for item in results
            ],
        }

    def _format_knowledge_context(self, retrieval_result) -> str:
        lines = ["[Knowledge retrieval evidence]"]
        lines.append(f"Status: {retrieval_result.status}")
        if retrieval_result.reason:
            lines.append(f"Reason: {retrieval_result.reason}")
        if retrieval_result.fallback_used:
            lines.append("Fallback: skill evidence was insufficient, so vector/BM25 retrieval was used.")
        if not retrieval_result.evidences:
            lines.append("No direct evidence was found.")
            return "\n".join(lines)

        for index, evidence in enumerate(retrieval_result.evidences, start=1):
            lines.append(
                f"{index}. [{evidence.channel}] {evidence.source_path} ({evidence.locator})\n{evidence.snippet}"
            )
        return "\n\n".join(lines)

    def _knowledge_answer_instructions(self, retrieval_result) -> list[str]:
        instructions = [
            "This is a knowledge-base question.",
            "Use only the provided knowledge retrieval evidence to answer.",
            "Do not perform additional knowledge-base inspection with tools.",
            "If the evidence is incomplete, explicitly say the current knowledge base only supports a partial answer or no direct answer.",
            "Do not fabricate facts.",
            "When evidence is insufficient, suggest narrowing the scope by directory, file, keyword, field name, or time range.",
            "Cite the file paths you relied on.",
        ]
        if retrieval_result.reason:
            instructions.append(f"Current retrieval note: {retrieval_result.reason}")
        return instructions

    async def _astream_model_answer(
        self,
        messages: list[dict[str, str]],
        extra_instructions: list[str] | None = None,
    ):
        if self.base_dir is None:
            raise RuntimeError("AgentManager is not initialized")

        system_prompt = build_system_prompt(self.base_dir, runtime_config.get_rag_mode())
        if extra_instructions:
            system_prompt = f"{system_prompt}\n\n" + "\n\n".join(extra_instructions)

        model_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        model_messages.extend(messages)

        final_content_parts: list[str] = []
        async for chunk in self._build_chat_model().astream(model_messages):
            text = _stringify_content(getattr(chunk, "content", ""))
            if text:
                final_content_parts.append(text)
                yield {"type": "token", "content": text}

        yield {"type": "done", "content": "".join(final_content_parts).strip()}

    async def _astream_agent_answer(
        self,
        messages: list[dict[str, str]],
        *,
        extra_instructions: list[str] | None = None,
    ):
        agent = self._build_agent(extra_instructions=extra_instructions)

        final_content_parts: list[str] = []
        last_ai_message = ""
        pending_tools: dict[str, dict[str, str]] = {}

        async for mode, payload in agent.astream(
            {"messages": messages},
            stream_mode=["messages", "updates"],
        ):
            if mode == "messages":
                chunk, metadata = payload
                if metadata.get("langgraph_node") != "model":
                    continue
                text = _stringify_content(getattr(chunk, "content", ""))
                if text:
                    final_content_parts.append(text)
                    yield {"type": "token", "content": text}
                continue

            if mode != "updates":
                continue

            for update in payload.values():
                for agent_message in update.get("messages", []):
                    message_type = getattr(agent_message, "type", "")
                    tool_calls = getattr(agent_message, "tool_calls", []) or []

                    if message_type == "ai" and not tool_calls:
                        candidate = _stringify_content(getattr(agent_message, "content", ""))
                        if candidate:
                            last_ai_message = candidate

                    if tool_calls:
                        for tool_call in tool_calls:
                            call_id = str(tool_call.get("id") or tool_call.get("name"))
                            tool_name = str(tool_call.get("name", "tool"))
                            tool_args = tool_call.get("args", "")
                            if not isinstance(tool_args, str):
                                tool_args = json.dumps(tool_args, ensure_ascii=False)
                            pending_tools[call_id] = {
                                "tool": tool_name,
                                "input": str(tool_args),
                            }
                            yield {
                                "type": "tool_start",
                                "tool": tool_name,
                                "input": str(tool_args),
                            }

                    if message_type == "tool":
                        tool_call_id = str(getattr(agent_message, "tool_call_id", ""))
                        pending = pending_tools.pop(
                            tool_call_id,
                            {"tool": getattr(agent_message, "name", "tool"), "input": ""},
                        )
                        output = _stringify_content(getattr(agent_message, "content", ""))
                        yield {
                            "type": "tool_end",
                            "tool": pending["tool"],
                            "output": output,
                        }
                        yield {"type": "new_response"}

        final_content = "".join(final_content_parts).strip() or last_ai_message.strip()
        yield {"type": "done", "content": final_content}

    def _build_workflow_instructions(self, plan: WorkflowPlan) -> list[str]:
        instructions: list[str] = []

        if plan.should_ask_clarification_first:
            instructions.append(
                "The current request is not ready for full execution yet. Ask a concise clarification question first and do not continue into a substantive answer."
            )
            if plan.trace.missing_context_types:
                missing = ", ".join(plan.trace.missing_context_types)
                instructions.append(f"Focus the clarification on these missing context types: {missing}.")

        if plan.handling_mode == "challenge":
            instructions.append(
                "Treat this as a challenge/correction turn. Re-evaluate the disputed point carefully, explain the basis, and avoid defending the previous answer blindly."
            )
        elif plan.handling_mode == "scope_info":
            instructions.append(
                "Treat this as a scope/capability question. Answer about what the system can or cannot do instead of executing the underlying task."
            )
        elif plan.handling_mode == "unsupported":
            instructions.append(
                "Treat this as an unsupported request. Refuse the operation briefly and, when possible, suggest a safer alternative."
            )

        if plan.route == "orchestrated":
            instructions.append(
                "This request requires explicit execution organization. Make the stages or subtask order visible before giving the final answer."
            )
        elif plan.route == "qa":
            instructions.append(
                "This request should stay within a single-turn answer flow. Keep the execution lightweight and avoid unnecessary planning narration."
            )
        elif plan.route == "chat":
            instructions.append(
                "This is a chat turn. Respond naturally and do not over-structure the answer."
            )

        if plan.use_planner:
            instructions.append(
                "Use an internal lightweight plan before answering so the reasoning order is stable."
            )
        if plan.decompose_query:
            instructions.append(
                "Cover each sub-question or subtask explicitly so no requested branch is skipped."
            )
        if plan.cite_sources:
            instructions.append(
                "Provide supporting basis or citations when available, and make the grounding visible instead of answering from bare assertion."
            )
        if plan.use_context:
            instructions.append(
                "Use the current conversation context and do not treat this as a standalone fresh request."
            )
        return instructions

    def _build_execution_summary_instructions(self, payload) -> list[str]:
        instructions: list[str] = []
        context_summary = payload.context_summary_view()
        plan_summary = payload.plan_summary_view()
        review_summary = payload.review_summary_view()
        evidence_summary = payload.evidence_summary_view()

        if context_summary.binding_summary != "not_applicable":
            instructions.append(
                f"Current binding summary: {context_summary.binding_summary}. Keep the answer anchored to the resolved target context."
            )
        if plan_summary.planning_mode != "not_applicable":
            instructions.append(
                f"Current planning summary: mode={plan_summary.planning_mode}, steps={plan_summary.step_count}, checkpoints={plan_summary.checkpoint_count}. Preserve this execution organization in the answer."
            )
            if plan_summary.fallback_used:
                instructions.append(
                    "Planning fell back to a conservative structure. Keep the answer compact and avoid over-claiming hidden execution detail."
                )
        if review_summary.review_mode != "not_applicable":
            instructions.append(
                f"Current review summary: mode={review_summary.review_mode}, scope={review_summary.review_scope}, confidence={review_summary.review_confidence}, status={review_summary.status_summary}."
            )
            if review_summary.needs_more_evidence_target_count:
                instructions.append(
                    f"There are still {review_summary.needs_more_evidence_target_count} target(s) needing more evidence. Acknowledge uncertainty explicitly."
                )
            if review_summary.follow_up_retrieval_attempted:
                instructions.append(
                    "A follow-up retrieval was attempted during review. Reflect any remaining uncertainty rather than implying the review was fully definitive."
                )
        if evidence_summary.retrieval_quality_status != "not_applicable":
            instructions.append(
                f"Current evidence summary: quality={evidence_summary.retrieval_quality_status}, evidences={evidence_summary.merged_evidence_count}, sources={evidence_summary.source_ref_count}."
            )
            if evidence_summary.missing_evidence:
                instructions.append(
                    "The evidence bundle is still incomplete. Do not overstate certainty and call out missing support when needed."
                )
        return instructions

    def _build_reject_response(self, plan: WorkflowPlan) -> str:
        if plan.handling_mode == "unsupported":
            return "这个请求目前不适合进入正常执行流。我不能直接协助这类操作，但如果你愿意，我可以改为帮你分析风险、约束条件，或整理一个更安全的处理方案。"
        return "这个请求当前不能按正常执行流继续处理。"

    def _load_session_scope(self, session_id: str | None) -> tuple[str, tuple[str, ...]]:
        if session_id is None or self.raw_session_manager is None:
            return DEFAULT_GROUP, (DEFAULT_GROUP,)

        session = self.raw_session_manager.get_session(session_id, DEFAULT_GROUP, DEFAULT_AGENT)
        if session is None:
            return DEFAULT_GROUP, (DEFAULT_GROUP,)

        metadata = session.metadata or {}
        active_group_id = str(metadata.get("active_group_id") or session.group_id or DEFAULT_GROUP)
        allowed = metadata.get("allowed_group_ids") or [active_group_id]
        allowed_group_ids = tuple(str(item) for item in allowed if item)
        if not allowed_group_ids:
            allowed_group_ids = (active_group_id,)
        return active_group_id, allowed_group_ids

    def _build_registry_entries_from_execution_payload(
        self,
        *,
        payload,
        session_id: str,
        tenant_id: str,
        group_id: str,
        message: str,
    ) -> list[ContextRegistryEntry]:
        turn_id = f"turn_{int(time.time() * 1000)}"
        summary_metadata = self._build_execution_summary_metadata(payload)
        context_bundle = payload.context_bundle_obj()
        plan_bundle = payload.plan_bundle_obj()
        review_bundle = payload.review_bundle_obj()
        entries: list[ContextRegistryEntry] = [
            ContextRegistryEntry(
                object_id=f"{turn_id}:question",
                object_type="question_object",
                tenant_id=tenant_id,
                group_id=group_id,
                session_id=session_id,
                source_turn_id=turn_id,
                content=message,
                refs=(payload.route, payload.handling_mode),
                salience_score=1.0,
                source_power="workflow",
                metadata={
                    "route": payload.route,
                    "handling_mode": payload.handling_mode,
                    **summary_metadata,
                },
            )
        ]

        if payload.evidence_bundle:
            for index, item in enumerate(payload.evidence_bundle.merged_evidence_items, start=1):
                entries.append(
                    ContextRegistryEntry(
                        object_id=f"{turn_id}:evidence:{index}",
                        object_type="evidence_ref",
                        tenant_id=tenant_id,
                        group_id=group_id,
                        session_id=session_id,
                        source_turn_id=turn_id,
                        content=item.snippet,
                        refs=(item.source_path, item.locator, *item.query_unit_ids),
                        salience_score=float(item.score or 0.0),
                        source_power="retrieval_power",
                        metadata={
                            "source_type": item.source_type,
                            "channel": item.channel,
                            "query_unit_ids": list(item.query_unit_ids),
                            **summary_metadata,
                        },
                    )
                )

        for index, target in enumerate(context_bundle.bound_targets(), start=1):
            object_type = str(target.get("object_type") or "question_object")
            if object_type not in {"claim", "evidence_ref", "retrieval_result_ref", "comparison_target", "case_or_scenario", "question_object"}:
                object_type = "question_object"
            entries.append(
                ContextRegistryEntry(
                    object_id=f"{turn_id}:bound:{index}",
                    object_type=object_type,
                    tenant_id=tenant_id,
                    group_id=group_id,
                    session_id=session_id,
                    source_turn_id=turn_id,
                    content=str(target.get("content", "")),
                    refs=tuple(str(ref) for ref in target.get("refs", ()) or (str(target.get("object_id", "")),)),
                    salience_score=0.9,
                    source_power="context_binding_power",
                    metadata={**dict(target), **summary_metadata},
                )
            )

        for index, unit in enumerate(plan_bundle.comparison_units, start=1):
            entries.append(
                ContextRegistryEntry(
                    object_id=f"{turn_id}:comparison:{index}",
                    object_type="comparison_target",
                    tenant_id=tenant_id,
                    group_id=group_id,
                    session_id=session_id,
                    source_turn_id=turn_id,
                    content=str(unit.get("label") or unit.get("content") or ""),
                    refs=(str(unit.get("unit_id", "")),),
                    salience_score=0.8,
                    source_power="planning_power",
                    metadata={**dict(unit), **summary_metadata},
                )
            )

        for index, unit in enumerate(plan_bundle.query_unit_dicts(), start=1):
            entries.append(
                ContextRegistryEntry(
                    object_id=f"{turn_id}:query-unit:{index}",
                    object_type="question_object",
                    tenant_id=tenant_id,
                    group_id=group_id,
                    session_id=session_id,
                    source_turn_id=turn_id,
                    content=str(unit.get("text", "")),
                    refs=(str(unit.get("unit_id", "")), str(unit.get("origin", ""))),
                    salience_score=0.75,
                    source_power="decomposition_power",
                    metadata={**dict(unit), **summary_metadata},
                )
            )

        for index, finding in enumerate(review_bundle.review_findings, start=1):
            entries.append(
                ContextRegistryEntry(
                    object_id=f"{turn_id}:claim:{index}",
                    object_type="claim",
                    tenant_id=tenant_id,
                    group_id=group_id,
                    session_id=session_id,
                    source_turn_id=turn_id,
                    content=str(finding.get("reason", "")),
                    refs=(str(finding.get("target_ref", "")),),
                    salience_score=1.0,
                    source_power="challenge_power",
                    metadata={**dict(finding), **summary_metadata},
                )
            )

        return entries[:10]

    def _build_execution_summary_metadata(self, payload) -> dict[str, Any]:
        context_bundle = payload.context_bundle_obj()
        plan_bundle = payload.plan_bundle_obj()
        review_bundle = payload.review_bundle_obj()
        context_summary = payload.context_summary_view()
        plan_summary_view = payload.plan_summary_view()
        review_summary_view = payload.review_summary_view()
        evidence_summary_view = payload.evidence_summary_view()

        evidence_summary = {}
        if getattr(payload, "evidence_bundle", None) is not None:
            evidence_summary = {
                "retrieval_quality_status": evidence_summary_view.retrieval_quality_status,
                "query_unit_count": evidence_summary_view.query_unit_count,
                "merged_evidence_count": evidence_summary_view.merged_evidence_count,
                "source_ref_count": evidence_summary_view.source_ref_count,
                "repairable_units": evidence_summary_view.repairable_units,
                "repaired_units": evidence_summary_view.repaired_units,
                "missing_evidence": evidence_summary_view.missing_evidence,
                "coverage_query_units": evidence_summary_view.coverage_query_units,
                "coverage_sources": evidence_summary_view.coverage_sources,
            }
        plan_summary = {
            "planning_mode": plan_summary_view.planning_mode,
            "step_count": plan_summary_view.step_count,
            "checkpoint_count": plan_summary_view.checkpoint_count,
            "comparison_unit_count": plan_summary_view.comparison_unit_count,
            "bound_target_ref_count": plan_summary_view.bound_target_ref_count,
            "refined": plan_summary_view.refined,
            "fallback_used": plan_summary_view.fallback_used,
            "fallback_reason": list(plan_bundle.fallback_reason),
        }
        review_summary = {
            "target_count": review_summary_view.target_count,
            "matched_target_count": review_summary_view.matched_target_count,
            "matched_target_refs": list(review_bundle.matched_target_refs()),
            "unsupported_target_refs": list(review_bundle.unsupported_target_refs()),
            "needs_more_evidence_targets": list(review_bundle.needs_more_evidence_targets()),
            "status_summary": review_summary_view.status_summary,
            "review_mode": review_summary_view.review_mode,
            "review_confidence": review_summary_view.review_confidence,
            "review_scope": review_summary_view.review_scope,
            "follow_up_retrieval_attempted": review_summary_view.follow_up_retrieval_attempted,
            "follow_up_retrieval_improved": review_summary_view.follow_up_retrieval_improved,
            "follow_up_retrieval_sources": list(review_bundle.follow_up_retrieval_sources()),
            "follow_up_retrieval_retrieved_evidence_count": review_bundle.follow_up_retrieval_retrieved_evidence_count(),
        }

        return {
            "knowledge_scope_status": str(getattr(payload, "knowledge_scope_status", "resolved")),
            "binding_summary": context_summary.binding_summary,
            "plan_summary": plan_summary,
            "review_summary": review_summary,
            "evidence_summary": evidence_summary,
        }

    def _persist_execution_payload(
        self,
        *,
        payload,
        session_id: str | None,
        group_id: str,
        message: str,
    ) -> None:
        if session_id is None or self.context_manager is None or self.raw_session_manager is None:
            return

        session = self.raw_session_manager.get_session(session_id, DEFAULT_GROUP, DEFAULT_AGENT)
        tenant_id = session.user_id if session is not None else "default"
        entries = self._build_registry_entries_from_execution_payload(
            payload=payload,
            session_id=session_id,
            tenant_id=tenant_id,
            group_id=group_id,
            message=message,
        )
        if not entries:
            return

        self.context_manager.append_registry_entries(
            tenant_id=tenant_id,
            group_id=group_id,
            agent_id=DEFAULT_AGENT,
            session_id=session_id,
            entries=entries,
        )

    def _load_recent_registry_entries(
        self,
        *,
        session_id: str | None,
        group_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if session_id is None or self.context_manager is None or self.raw_session_manager is None:
            return []

        session = self.raw_session_manager.get_session(session_id, DEFAULT_GROUP, DEFAULT_AGENT)
        tenant_id = session.user_id if session is not None else "default"
        entries = self.context_manager.list_recent_registry_entries(
            tenant_id=tenant_id,
            group_id=group_id,
            agent_id=DEFAULT_AGENT,
            session_id=session_id,
            limit=limit,
        )
        return [entry.to_dict() for entry in entries]

    async def astream(
        self,
        message: str,
        history: list[dict[str, Any]],
        session_id: str | None = None,
    ):
        if self.base_dir is None:
            raise RuntimeError("AgentManager is not initialized")

        rag_mode = runtime_config.get_rag_mode()
        messages = await self._prepare_messages_for_request(session_id, message, history)
        active_group_id, allowed_group_ids = self._load_session_scope(session_id)
        intent_assets = load_group_intent_rule_assets(self.base_dir / "storage", active_group_id)
        intent_analysis = classify_intent(message, history, rule_assets=intent_assets)
        registry_entries = self._load_recent_registry_entries(
            session_id=session_id,
            group_id=active_group_id,
        )
        workflow_plan = build_workflow_plan(
            intent_analysis,
            is_knowledge_query=self._is_knowledge_query(message),
            active_group_id=active_group_id,
            allowed_group_ids=allowed_group_ids,
        )
        execution_payload = self.workflow_dispatcher.dispatch(workflow_plan).run(
            workflow_plan,
            RouteExecutionRequest(
                message=message,
                messages=messages,
                is_knowledge_query=self._is_knowledge_query(message),
                context={
                    "session_id": session_id,
                    "active_group_id": active_group_id,
                    "allowed_group_ids": allowed_group_ids,
                    "registry_entries": registry_entries,
                    "recent_power": registry_entries[-1].get("source_power") if registry_entries else None,
                    "recent_object_type": registry_entries[-1].get("object_type") if registry_entries else None,
                },
            ),
        )

        if rag_mode:
            retrievals = memory_indexer.retrieve(message, top_k=3)
            if retrievals:
                yield {"type": "retrieval", **self._format_memory_retrieval_step(retrievals)}
            if retrievals:
                messages = self._insert_before_latest_user(
                    messages,
                    {
                        "role": "assistant",
                        "content": self._format_retrieval_context(retrievals),
                    },
                )

        workflow_instructions = list(execution_payload.instructions) or self._build_workflow_instructions(workflow_plan)
        workflow_instructions.extend(self._build_execution_summary_instructions(execution_payload))

        if execution_payload.action == "reject":
            async for event in self._astream_model_answer(
                messages,
                extra_instructions=workflow_instructions + [self._build_reject_response(workflow_plan)],
            ):
                yield event
            self._persist_execution_payload(
                payload=execution_payload,
                session_id=session_id,
                group_id=active_group_id,
                message=message,
            )
            return

        if execution_payload.action == "respond":
            async for event in self._astream_model_answer(
                messages,
                extra_instructions=workflow_instructions,
            ):
                yield event
            self._persist_execution_payload(
                payload=execution_payload,
                session_id=session_id,
                group_id=active_group_id,
                message=message,
            )
            return

        if execution_payload.action == "knowledge_orchestrator":
            knowledge_result = None
            async for event in knowledge_orchestrator.astream(message):
                if event.get("type") == "orchestrated_result":
                    knowledge_result = event["result"]
                    continue
                yield event

            if knowledge_result is not None:
                for step in knowledge_result.steps:
                    yield {"type": "retrieval", **step.to_dict()}
                messages = self._insert_before_latest_user(
                    messages,
                    {
                        "role": "assistant",
                        "content": self._format_knowledge_context(knowledge_result),
                    },
                )
                execution_payload = replace(
                    execution_payload,
                    evidence_bundle=self.retrieval_power.build_bundle_from_orchestrated_result(
                        knowledge_result,
                        query=message,
                    ),
                )

            async for event in self._astream_model_answer(
                messages,
                extra_instructions=workflow_instructions
                + (self._knowledge_answer_instructions(knowledge_result) if knowledge_result else []),
            ):
                yield event
            self._persist_execution_payload(
                payload=execution_payload,
                session_id=session_id,
                group_id=active_group_id,
                message=message,
            )
            return

        async for event in self._astream_agent_answer(
            messages,
            extra_instructions=workflow_instructions,
        ):
            yield event
        self._persist_execution_payload(
            payload=execution_payload,
            session_id=session_id,
            group_id=active_group_id,
            message=message,
        )

    async def generate_title(self, first_user_message: str) -> str:
        prompt = (
            "请根据用户的第一条消息生成一个中文会话标题。"
            "要求不超过 10 个汉字，不要带引号，不要解释。"
        )
        try:
            response = await self._build_chat_model().ainvoke(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": first_user_message},
                ]
            )
            title = _stringify_content(getattr(response, "content", "")).strip()
            return title[:10] or "新会话"
        except Exception:
            return (first_user_message.strip() or "新会话")[:10]

    async def summarize_history(self, messages: list[dict[str, Any]]) -> str:
        prompt = (
            "请将以下对话压缩成中文摘要，控制在 500 字以内。"
            "重点保留用户目标、已完成步骤、重要结论和未解决事项。"
        )
        lines: list[str] = []
        for item in messages:
            role = item.get("role", "assistant")
            content = str(item.get("content", "") or "")
            if content:
                lines.append(f"{role}: {content}")
        transcript = "\n".join(lines)

        try:
            response = await self._build_chat_model().ainvoke(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": transcript},
                ]
            )
            summary = _stringify_content(getattr(response, "content", "")).strip()
            return summary[:500]
        except Exception:
            return transcript[:500]


agent_manager = AgentManager()
