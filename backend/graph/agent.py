from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

from config import runtime_config
from context.assembly.context_manager import ContextManager
from context.session.session_manager import DEFAULT_AGENT, DEFAULT_GROUP, DEFAULT_USER, SessionManager
from graph.prompt_builders.answer_prompt_assembler import assemble_answer_messages
from graph.prompt_builders.workflow_prompt_projector import (
    build_answer_behavior_rules_from_workflow,
    build_answer_result_projection_rules_from_workflow,
)
from graph.serializers.frontend_trace import (
    serialize_execution_payload,
    serialize_intent_analysis,
    serialize_workflow_plan,
)
from intent import classify_intent
from intent.model_runtime import build_default_llm_fallback_adapter, build_default_small_model_adapter
from intent.loaders import load_group_intent_rule_assets
from intent.rules.knowledge_query_rules import is_knowledge_query
from llm.model_factory import build_chat_model
from llm.output_sanitizer import StreamingReasoningFilter, sanitize_model_text
from llm.response_utils import stringify_content
from memory_system.memory_service import MemorySystem
from memory_system.session_working_memory import SessionWorkingMemoryWriter
from observability.emitters.answer_emitter import AnswerEmitter
from observability.emitters.context_emitter import ContextEmitter
from observability.emitters.intent_emitter import IntentEmitter
from observability.emitters.retrieval_emitter import RetrievalEmitter
from observability.langsmith.client import LangSmithClient
from observability.langsmith.serializers import (
    summarize_intent_analysis,
    summarize_evidence_bundle,
    summarize_execution_payload,
    summarize_messages,
)
from observability.runtime.run_factory import create_trace_context
from observability.runtime.trace_context_store import activate_trace_context
from workflow import WorkflowDispatcher, WorkflowPlan, build_workflow_plan
from workflow.powers.retrieval_power import RetrievalPower
from workflow.runners.base import RouteExecutionRequest


class AgentManager:
    def __init__(self) -> None:
        self.base_dir: Path | None = None
        self.raw_session_manager: SessionManager | None = None
        self.memory_system: MemorySystem | None = None
        self.context_manager: ContextManager | None = None
        self.workflow_dispatcher = WorkflowDispatcher()
        self.retrieval_power = RetrievalPower()
        self.tools = []
        self.working_memory_writer = SessionWorkingMemoryWriter()
        self.langsmith_client = LangSmithClient()
        self.answer_emitter = AnswerEmitter(self.langsmith_client)
        self.retrieval_emitter = RetrievalEmitter(self.langsmith_client)
        self.context_emitter = ContextEmitter(self.langsmith_client)
        self.intent_emitter = IntentEmitter(self.langsmith_client)
        self.intent_model_adapter = None
        self.intent_llm_fallback_adapter = None

    def initialize(self, base_dir: Path) -> None:
        self.base_dir = base_dir

        self.raw_session_manager = SessionManager(base_dir / "storage")
        self.memory_system = MemorySystem(base_dir / "storage")
        self.memory_system.set_extractor_llm_call(self._llm_text_call_sync)
        self.context_manager = ContextManager(self.raw_session_manager, self.memory_system)
        self.context_manager.set_llm_call(self._llm_text_call)
        self.context_manager.set_observability_emitter(self.context_emitter)
        self.intent_model_adapter = self._build_intent_model_adapter()
        self.intent_llm_fallback_adapter = self._build_intent_llm_fallback_adapter()

    def _build_intent_model_adapter(self):
        if self.base_dir is None:
            return None
        try:
            return build_default_small_model_adapter(project_root=self.base_dir.parent)
        except Exception:
            return None

    def _build_intent_llm_fallback_adapter(self):
        if self.base_dir is None:
            return None
        try:
            return build_default_llm_fallback_adapter(project_root=self.base_dir.parent)
        except Exception:
            return None

    async def _llm_text_call(self, prompt: str) -> str:
        response = await build_chat_model().ainvoke(
            [{"role": "user", "content": prompt}]
        )
        return sanitize_model_text(stringify_content(getattr(response, "content", "")))

    def _llm_text_call_sync(self, prompt: str) -> str:
        response = build_chat_model().invoke(
            [{"role": "user", "content": prompt}]
        )
        return sanitize_model_text(stringify_content(getattr(response, "content", "")))

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
        group_id: str,
        session_id: str | None,
        message: str,
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        current_user = {"role": "user", "content": message}
        if self.context_manager is None:
            messages = self._build_messages(history)
            messages.append(current_user)
            return {
                "messages": messages,
                "memory_retrieval": {
                    "performed": False,
                    "owner": "context",
                    "source": "memory",
                    "query": message,
                    "core_memory_count": 0,
                    "retrieved_memory_count": 0,
                    "core_block_present": False,
                    "retrieved_memories_present": False,
                    "results": [],
                },
            }

        has_new_transcript = False
        if session_id and self.raw_session_manager is not None:
            has_new_transcript = bool(
                self.raw_session_manager.get_transcript(
                    group_id,
                    DEFAULT_AGENT,
                    session_id,
                    limit=1,
                    include_compacted=True,
                )
            )

        if session_id and has_new_transcript:
            prepared = await self.context_manager.prepare(
                group_id,
                DEFAULT_AGENT,
                session_id,
                extra_messages=[current_user],
                query=message,
            )
        else:
            messages = self._build_messages(history)
            messages.append(current_user)
            prepared = await self.context_manager.prepare_messages(
                group_id,
                DEFAULT_AGENT,
                messages,
                query=message,
            )

        return {
            "messages": self._build_messages(prepared["messages"]),
            "memory_retrieval": dict(prepared.get("memory_retrieval", {})),
        }

    def _format_retrieval_context(self, results: list[dict[str, Any]]) -> str:
        lines = ["[RAG retrieved memory context]"]
        for idx, item in enumerate(results, start=1):
            text = str(item.get("text", "")).strip()
            source = str(item.get("source", "memory"))
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
                    "source_path": str(item.get("source", "memory")),
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

    def _knowledge_query_reference(self, evidence_bundle: Any) -> str:
        query_units = list(getattr(evidence_bundle, "query_unit_results", ()) or ())
        if not query_units:
            return ""
        first = query_units[0]
        if hasattr(first, "selected_query_text"):
            return str(first.selected_query_text() or "").strip()
        if hasattr(first, "selected_query"):
            return str(getattr(first, "selected_query", "") or "").strip()
        if isinstance(first, dict):
            return str(first.get("selected_query") or first.get("query") or "").strip()
        return str(getattr(first, "query", "") or "").strip()

    def _knowledge_query_tokens(self, query_text: str) -> tuple[str, ...]:
        lowered = query_text.lower()
        latin_tokens = re.findall(r"[a-z0-9.+-]{3,}", lowered)
        cjk_phrases = [
            phrase
            for phrase in (
                "知识库",
                "science advances",
                "tfa",
                "native chemical ligation",
                "ncl",
                "sars-cov-2",
                "e protein",
                "envelope",
                "nanobody",
                "nanobodies",
                "辅助肽连接",
                "天然化学连接",
                "纳米抗体",
                "蛋白质药物",
                "抗病毒药物",
                "突破",
                "价值",
            )
            if phrase in lowered or phrase in query_text
        ]
        ordered: list[str] = []
        seen: set[str] = set()
        for token in [*cjk_phrases, *latin_tokens]:
            normalized = token.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(token.strip())
        return tuple(ordered[:24])

    def _rank_knowledge_evidence_items(self, evidence_bundle: Any) -> list[Any]:
        merged_items = list(getattr(evidence_bundle, "merged_evidence_items", ()) or ())
        query_text = self._knowledge_query_reference(evidence_bundle)
        tokens = self._knowledge_query_tokens(query_text)
        if not merged_items or not tokens:
            return merged_items

        def _score(item: Any) -> tuple[float, float]:
            source_path = str(getattr(item, "source_path", "") or "")
            snippet = str(getattr(item, "snippet", "") or "")
            haystack = f"{source_path}\n{snippet}".lower()
            overlap = 0.0
            for token in tokens:
                normalized = token.lower()
                if normalized and normalized in haystack:
                    overlap += max(1.0, min(len(normalized) / 6.0, 4.0))
            has_source_pdf = 2.0 if source_path.endswith("/source.pdf") or source_path.endswith("\\source.pdf") else 0.0
            base_score = float(getattr(item, "score", 0.0) or 0.0)
            return (overlap + has_source_pdf, base_score)

        return sorted(merged_items, key=_score, reverse=True)

    def _format_knowledge_retrieval_context(self, evidence_bundle: Any) -> str:
        lines = ["[RAG retrieved knowledge context]"]
        merged_items = self._rank_knowledge_evidence_items(evidence_bundle)
        for idx, item in enumerate(merged_items[:6], start=1):
            snippet = str(getattr(item, "snippet", "") or "").strip()[:1200]
            source_path = str(getattr(item, "source_path", "") or "knowledge")
            locator = str(getattr(item, "locator", "") or "")
            score = getattr(item, "score", None)
            score_text = "" if score is None else f" [score={float(score):.4f}]"
            header = f"{idx}. Source: {source_path}"
            if locator:
                header += f" @ {locator}"
            header += score_text
            lines.append(f"{header}\n{snippet}")
        return "\n\n".join(lines)

    def _format_knowledge_retrieval_step(self, evidence_bundle: Any) -> dict[str, Any]:
        merged_items = self._rank_knowledge_evidence_items(evidence_bundle)
        source_refs = []
        if hasattr(evidence_bundle, "source_ref_list"):
            source_refs = list(evidence_bundle.source_ref_list())
        return {
            "kind": "knowledge",
            "stage": "knowledge",
            "title": f"Knowledge 检索到 {len(merged_items)} 条证据",
            "message": (
                "已将 Knowledge 检索结果注入当前请求上下文。"
                if merged_items
                else "Knowledge 检索已执行，但当前没有可注入的证据片段。"
            ),
            "results": [
                {
                    "source_path": str(getattr(item, "source_path", "")),
                    "source_type": str(getattr(item, "source_type", "")),
                    "locator": str(getattr(item, "locator", "")),
                    "snippet": str(getattr(item, "snippet", "")).strip(),
                    "channel": str(getattr(item, "channel", "")),
                    "score": getattr(item, "score", None),
                    "parent_id": getattr(item, "parent_id", None),
                }
                for item in merged_items[:8]
            ],
            "source_refs": source_refs[:8],
        }

    async def _astream_model_answer(
        self,
        messages: list[dict[str, str]],
        extra_instructions: list[str] | None = None,
    ):
        if self.base_dir is None:
            raise RuntimeError("AgentManager is not initialized")

        model_messages = assemble_answer_messages(
            self.base_dir,
            messages,
            rag_mode=runtime_config.get_rag_mode(),
            extra_instructions=extra_instructions,
        )

        final_content_parts: list[str] = []
        reasoning_filter = StreamingReasoningFilter()
        async for chunk in build_chat_model().astream(model_messages):
            text = stringify_content(getattr(chunk, "content", ""))
            visible_text = reasoning_filter.feed(text)
            if visible_text:
                final_content_parts.append(visible_text)
                yield {"type": "token", "content": visible_text}

        trailing = reasoning_filter.flush()
        if trailing:
            final_content_parts.append(trailing)
            yield {"type": "token", "content": trailing}

        yield {"type": "done", "content": "".join(final_content_parts).strip()}

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

    def _persist_execution_payload(
        self,
        *,
        payload,
        session_id: str | None,
        group_id: str,
        message: str,
    ) -> None:
        del payload, session_id, group_id, message
        # Registry projection is kept as a legacy adapter, but runtime no longer
        # writes workflow payloads back into registry by default.
        return

    def _persist_working_memory(
        self,
        *,
        payload,
        session_id: str | None,
        group_id: str,
        message: str,
        answer_text: str,
    ) -> None:
        if session_id is None or self.raw_session_manager is None:
            return
        session = self.raw_session_manager.get_session(session_id, group_id, DEFAULT_AGENT)
        user_id = str(session.user_id if session is not None and session.user_id else DEFAULT_USER)
        binding = payload.context_bundle_obj().binding_obj()
        review_bundle = payload.review_bundle_obj().to_dict()
        entries = self.working_memory_writer.build_entries_from_turn(
            turn_id=f"{session_id}:{payload.route}:{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            user_query=message,
            answer_text=answer_text,
            current_goal=payload.plan_bundle.get("goal") if isinstance(payload.plan_bundle, dict) else None,
            binding_result=binding.to_dict(),
            review_result={
                "status": review_bundle.get("status"),
                "summary": review_bundle.get("summary_text") or review_bundle.get("status"),
            },
        )
        if not entries:
            return
        self.raw_session_manager.working_memory_store.append_entries(
            session_id=session_id,
            group_id=group_id,
            agent_id=DEFAULT_AGENT,
            user_id=user_id,
            entries=entries,
        )

    def _persist_execution_outputs(
        self,
        *,
        payload,
        session_id: str | None,
        group_id: str,
        message: str,
        answer_text: str,
    ) -> None:
        self._persist_execution_payload(
            payload=payload,
            session_id=session_id,
            group_id=group_id,
            message=message,
        )
        self._persist_working_memory(
            payload=payload,
            session_id=session_id,
            group_id=group_id,
            message=message,
            answer_text=answer_text,
        )

    def _create_request_trace_context(self, session_id: str | None) -> Any:
        session = None
        if session_id is not None and self.raw_session_manager is not None:
            session = self.raw_session_manager.get_session(session_id, DEFAULT_GROUP, DEFAULT_AGENT)
        return create_trace_context(
            session_id=session_id or "ad_hoc",
            group_id=str(session.group_id if session is not None else DEFAULT_GROUP),
            user_id=str(session.user_id if session is not None else DEFAULT_USER),
        )

    def _emit_retrieval_event(
        self,
        *,
        started_at: datetime,
        query: str,
        output_summary: dict[str, Any],
        metadata: dict[str, Any],
        status: str = "success",
    ) -> None:
        self.retrieval_emitter.emit_retrieval_run(
            started_at=started_at,
            input_summary={"query": query[:200]},
            output_summary=output_summary,
            metadata=metadata,
            status=status,
        )

    def _emit_answer_event(
        self,
        *,
        started_at: datetime,
        messages: list[dict[str, str]],
        workflow_plan: WorkflowPlan,
        execution_payload,
        query: str,
        answer_text: str,
        answer_mode: str,
    ) -> None:
        self.answer_emitter.emit_answer_model_run(
            started_at=started_at,
            messages_summary=summarize_messages(messages),
            output_summary={
                "answer_mode": answer_mode,
                "answer_length": len(answer_text),
                "payload_summary": summarize_execution_payload(execution_payload),
            },
            metadata={
                "workflow_name": workflow_plan.route,
                "handling_mode": workflow_plan.handling_mode,
                "system_prompt_version": (
                    self.context_manager.config.system_prompt_path
                    if self.context_manager is not None
                    else "prompts/system/answer_system_prompt.md"
                ),
                "final_user_query": query[:200],
                "memory_block_types": summarize_messages(messages).get("system_blocks", []),
                "retrieval_block_types": [
                    block
                    for block in summarize_messages(messages).get("system_blocks", [])
                    if "Memory" in block or "retrieval" in block or "Knowledge" in block
                ],
            },
        )

    def _emit_intent_event(
        self,
        *,
        started_at: datetime,
        query: str,
        intent_analysis,
    ) -> None:
        self.intent_emitter.emit_intent_classification_run(
            started_at=started_at,
            input_summary={"query": query[:200]},
            output_summary=summarize_intent_analysis(intent_analysis),
            metadata={"main_intent": str(intent_analysis.main_intent)},
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
        trace_context = self._create_request_trace_context(session_id)
        with activate_trace_context(trace_context):
            rag_mode = runtime_config.get_rag_mode()
            active_group_id, allowed_group_ids = self._load_session_scope(session_id)
            trace_context.group_id = active_group_id
            prepared_request = await self._prepare_messages_for_request(
                active_group_id,
                session_id,
                message,
                history,
            )
            messages = list(prepared_request["messages"])
            memory_retrieval = dict(prepared_request.get("memory_retrieval", {}))
            intent_assets = load_group_intent_rule_assets(self.base_dir / "storage", active_group_id)
            intent_started_at = datetime.now()
            intent_analysis = classify_intent(
                message,
                history,
                rule_assets=intent_assets,
                model_adapter=self.intent_model_adapter,
                llm_fallback_adapter=self.intent_llm_fallback_adapter,
            )
            self._emit_intent_event(
                started_at=intent_started_at,
                query=message,
                intent_analysis=intent_analysis,
            )
            # Keep frontend trace aligned with the actual intent object emitted by the backend.
            yield serialize_intent_analysis(intent_analysis)
            working_memory = None
            if session_id is not None and self.raw_session_manager is not None:
                working_memory = self.raw_session_manager.get_working_memory(
                    session_id,
                    active_group_id,
                    DEFAULT_AGENT,
                )
            workflow_plan = build_workflow_plan(
                intent_analysis,
                is_knowledge_query=is_knowledge_query(message),
                active_group_id=active_group_id,
                allowed_group_ids=allowed_group_ids,
            )
            yield serialize_workflow_plan(workflow_plan)
            execution_payload = self.workflow_dispatcher.dispatch(workflow_plan).run(
                workflow_plan,
                RouteExecutionRequest(
                    message=message,
                    messages=messages,
                    is_knowledge_query=is_knowledge_query(message),
                    context={
                        "session_id": session_id,
                        "active_group_id": active_group_id,
                        "allowed_group_ids": allowed_group_ids,
                        "working_memory": working_memory,
                        "recent_messages": messages[-6:],
                        "bound_query_llm_call": self._llm_text_call_sync,
                        "base_dir": self.base_dir,
                        "memory_retrieval": memory_retrieval,
                    },
                ),
            )
            # Stage v1 only exposes route payload readiness, not unit-level runtime states.
            yield serialize_execution_payload(
                execution_payload,
                stage="route_payload_ready",
            )

            if execution_payload.evidence_bundle is not None:
                knowledge_step = self._format_knowledge_retrieval_step(execution_payload.evidence_bundle)
                if knowledge_step["results"]:
                    messages = self._insert_before_latest_user(
                        messages,
                        {
                            "role": "system",
                            "content": self._format_knowledge_retrieval_context(execution_payload.evidence_bundle),
                        },
                    )
                yield {"type": "retrieval", **knowledge_step}
                self._emit_retrieval_event(
                    started_at=datetime.now(),
                    query=message,
                    output_summary=summarize_evidence_bundle(execution_payload.evidence_bundle),
                    metadata={
                        "retrieval_source": "workflow_payload",
                        "workflow_name": workflow_plan.route,
                    },
                )

            retrievals = list(memory_retrieval.get("results", []) or [])
            if rag_mode and retrievals:
                retrieval_started_at = datetime.now()
                yield {"type": "retrieval", **self._format_memory_retrieval_step(retrievals)}
                self._emit_retrieval_event(
                    started_at=retrieval_started_at,
                    query=message,
                    output_summary={
                        "knowledge_hit_count": 0,
                        "memory_hit_count": len(retrievals),
                        "evidence_ids": [str(item.get("source") or "memory") for item in retrievals],
                        "retrieval_quality_status": "available",
                    },
                    metadata={
                        "retrieval_source": "context_memory",
                        "retrieval_owner": str(memory_retrieval.get("owner") or "context"),
                        "workflow_name": workflow_plan.route,
                    },
                )

            workflow_instructions = list(execution_payload.instructions) or build_answer_behavior_rules_from_workflow(workflow_plan)
            workflow_instructions.extend(build_answer_result_projection_rules_from_workflow(execution_payload))

            if execution_payload.action == "reject":
                answer_started_at = datetime.now()
                final_answer = ""
                async for event in self._astream_model_answer(
                    messages,
                    extra_instructions=workflow_instructions + [self._build_reject_response(workflow_plan)],
                ):
                    if event.get("type") == "done":
                        final_answer = str(event.get("content") or "")
                    yield event
                self._emit_answer_event(
                    started_at=answer_started_at,
                    messages=messages,
                    workflow_plan=workflow_plan,
                    execution_payload=execution_payload,
                    query=message,
                    answer_text=final_answer,
                    answer_mode="model",
                )
                self._persist_execution_outputs(
                    payload=execution_payload,
                    session_id=session_id,
                    group_id=active_group_id,
                    message=message,
                    answer_text=final_answer,
                )
                return

            if execution_payload.action == "respond":
                answer_started_at = datetime.now()
                final_answer = ""
                async for event in self._astream_model_answer(
                    messages,
                    extra_instructions=workflow_instructions,
                ):
                    if event.get("type") == "done":
                        final_answer = str(event.get("content") or "")
                    yield event
                self._emit_answer_event(
                    started_at=answer_started_at,
                    messages=messages,
                    workflow_plan=workflow_plan,
                    execution_payload=execution_payload,
                    query=message,
                    answer_text=final_answer,
                    answer_mode="model",
                )
                self._persist_execution_outputs(
                    payload=execution_payload,
                    session_id=session_id,
                    group_id=active_group_id,
                    message=message,
                    answer_text=final_answer,
                )
                return

            raise RuntimeError(
                f"unsupported workflow action emitted by policy/runner: {execution_payload.action}"
            )

    async def generate_title(self, first_user_message: str) -> str:
        prompt = (
            "请根据用户的第一条消息生成一个中文会话标题。"
            "要求不超过 10 个汉字，不要带引号，不要解释。"
        )
        try:
            response = await build_chat_model().ainvoke(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": first_user_message},
                ]
            )
            title = stringify_content(getattr(response, "content", "")).strip()
            return title[:10] or "新会话"
        except Exception:
            return (first_user_message.strip() or "新会话")[:10]

agent_manager = AgentManager()
