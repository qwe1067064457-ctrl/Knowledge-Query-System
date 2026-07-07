from __future__ import annotations

from dataclasses import replace

from context.session import DEFAULT_AGENT
from memory_system.memory_anchor import MemoryAnchor
from workflow.powers.retrieval_power import RetrievalPower
from workflow.retrieval_gate import RetrievalGate
from workflow.helpers.knowledge_query_rewrite_helper import KnowledgeQueryRewriteHelper
from workflow.orchestrated.execution_layer.adapters.retrieval_adapter import build_retrieval_workers
from workflow.orchestrated.execution_layer.workers.registry import WorkerRegistry
from workflow.routes.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import QueryUnit, WorkflowPlan
from workflow.workers.memory_anchor_worker import MemoryAnchorWorker
from workflow.workers.review_worker import ReviewWorker


def _merge_key_events(*event_groups: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in event_groups:
        for item in group:
            if item and item not in merged:
                merged.append(str(item))
    return tuple(merged)


def _retrieval_events(*, retrieval_quality: dict[str, object], repaired_units: int, missing_evidence: bool) -> tuple[str, ...]:
    events = ["retrieval_performed"]
    if repaired_units > 0:
        events.append("retrieval_repaired")
    if missing_evidence or retrieval_quality.get("status") == "bad":
        events.append("retrieval_quality_weak")
    return tuple(events)


class QaRouteRunner(BaseRouteRunner):
    route_name = "qa"

    def __init__(self) -> None:
        self.review_worker = ReviewWorker()
        self.memory_anchor_worker = MemoryAnchorWorker()
        self.knowledge_query_rewrite_helper = KnowledgeQueryRewriteHelper()
        self.retrieval_power = RetrievalPower()
        self.retrieval_gate = RetrievalGate()

    def _build_worker_registry(self) -> WorkerRegistry:
        registry = WorkerRegistry()
        for worker in build_retrieval_workers(
            retrieval_power=self.retrieval_power,
            review_worker=self.review_worker,
        ):
            registry.register(worker)
        return registry

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        worker_registry = self._build_worker_registry()
        payload = self._build_payload(
            plan,
            request,
            ("This request should stay within a single-turn answer flow. Keep execution lightweight and avoid unnecessary planning narration.",),
        )
        context_bundle = payload.context_bundle_obj()
        answer_constraints = dict(payload.answer_constraints)
        key_events: tuple[str, ...] = ()
        _, _, memory_anchor_count, hydrated_memory_entry_count = self._prepare_memory_anchor_context(
            plan=plan,
            request=request,
        )
        if hydrated_memory_entry_count:
            key_events = _merge_key_events(key_events, ("memory_anchor_hydrated",))
        context_bundle = replace(
            context_bundle,
            memory_anchor_count=memory_anchor_count,
            hydrated_memory_entry_count=hydrated_memory_entry_count,
            memory_hydrated=hydrated_memory_entry_count > 0,
        )
        context_bundle = self._normalize_context_bundle_obj(plan, context_bundle)

        evidence_bundle = payload.evidence_bundle
        knowledge_path_filters = self._knowledge_path_filters(request)
        retrieval_decision = self.retrieval_gate.decide(
            plan=plan,
            request=request,
        )
        if "retrieval_power" in plan.enabled_powers and retrieval_decision.should_retrieve:
            query_text = request.message.strip()
            if request.is_knowledge_query:
                rewrite_payload = self.knowledge_query_rewrite_helper.rewrite(
                    query_text,
                    llm_call=request.context.get("bound_query_llm_call"),
                )
                query_text = str(rewrite_payload.get("query") or query_text).strip() or query_text
                if bool(rewrite_payload.get("applied", False)):
                    key_events = _merge_key_events(key_events, ("knowledge_query_rewritten",))
            query_units = (
                QueryUnit(
                    unit_id="primary",
                    text=query_text,
                    origin="primary",
                ),
            )
            evidence_bundle = self.retrieval_power.retrieve(
                query_units,
                path_filters=knowledge_path_filters,
            )
            retrieval_quality_worker = worker_registry.get("retrieval_quality")
            retrieval_quality = retrieval_quality_worker(evidence_bundle=evidence_bundle)
            key_events = _merge_key_events(
                key_events,
                _retrieval_events(
                    retrieval_quality=retrieval_quality,
                    repaired_units=evidence_bundle.repaired_unit_count(),
                    missing_evidence=evidence_bundle.missing_evidence_flag(),
                ),
            )
            if retrieval_decision.should_clarify_first and payload.status == "ready":
                payload = replace(payload, status="needs_clarification")

        return self._finalize_payload(
            payload,
            plan,
            context_bundle=context_bundle,
            plan_bundle=payload.plan_bundle,
            answer_constraints=answer_constraints,
            key_events=key_events,
            evidence_bundle=evidence_bundle,
        )

    def _knowledge_path_filters(self, request: RouteExecutionRequest) -> tuple[str, ...]:
        # Knowledge retrieval should stay inside the active group unless a future runtime
        # explicitly asks to broaden scope.
        active_group_id = str(request.context.get("active_group_id") or "").strip()
        if not active_group_id:
            return ()
        return (f"storage/groups/{active_group_id}/knowledge",)

    def _prepare_memory_anchor_context(
        self,
        *,
        plan: WorkflowPlan,
        request: RouteExecutionRequest,
    ) -> tuple[list[dict[str, str]], list[dict[str, object]], int, int]:
        memory_anchors = list(request.context.get("memory_anchors") or ())
        recent_messages = [
            {"role": str(item.get("role", "")), "content": str(item.get("content", ""))}
            for item in request.context.get("recent_messages", ()) or ()
            if item.get("content")
        ]
        existing_hydrated = list(request.context.get("hydrated_memory_context") or ())
        if existing_hydrated:
            hydrated_messages = self._project_hydrated_messages(existing_hydrated)
            hydrated_candidates = self._project_hydrated_candidates(existing_hydrated)
            return (
                [*hydrated_messages, *recent_messages],
                hydrated_candidates,
                len(memory_anchors),
                len(existing_hydrated),
            )
        if not self._should_hydrate_memory_anchors(plan=plan, request=request, memory_anchors=memory_anchors):
            return recent_messages, [], len(memory_anchors), 0

        session_manager = request.context.get("session_manager")
        group_id = str(request.context.get("group_id") or request.context.get("active_group_id") or "").strip()
        agent_id = str(request.context.get("agent_id") or DEFAULT_AGENT).strip() or DEFAULT_AGENT
        if session_manager is None or not group_id:
            return recent_messages, [], len(memory_anchors), 0

        hydrated_entries: list[dict[str, object]] = []
        seen_entry_ids: set[str] = set()
        for anchor_payload in memory_anchors:
            anchor = self._coerce_memory_anchor(anchor_payload)
            if anchor is None or not anchor.can_hydrate_context:
                continue
            for entry in self.memory_anchor_worker.hydrate_context(
                anchor=anchor,
                session_manager=session_manager,
                group_id=group_id,
                agent_id=agent_id,
            ):
                entry_id = str(entry.get("id") or entry.get("content") or "").strip()
                if entry_id and entry_id in seen_entry_ids:
                    continue
                if entry_id:
                    seen_entry_ids.add(entry_id)
                hydrated_entries.append(dict(entry))

        if not hydrated_entries:
            return recent_messages, [], len(memory_anchors), 0

        request.context["hydrated_memory_context"] = [dict(item) for item in hydrated_entries]
        request.context["memory_anchor_hydrated"] = True
        request.context["hydrated_memory_entry_count"] = len(hydrated_entries)
        hydrated_messages = self._project_hydrated_messages(hydrated_entries)
        hydrated_candidates = self._project_hydrated_candidates(hydrated_entries)
        return (
            [*hydrated_messages, *recent_messages],
            hydrated_candidates,
            len(memory_anchors),
            len(hydrated_entries),
        )

    def _should_hydrate_memory_anchors(
        self,
        *,
        plan: WorkflowPlan,
        request: RouteExecutionRequest,
        memory_anchors: list[dict[str, object]],
    ) -> bool:
        if not memory_anchors:
            return False
        if bool(request.context.get("memory_anchor_summary_sufficient", False)):
            return False
        return bool(
            plan.use_context
            or plan.handling_mode == "challenge"
            or plan.policy_flags.need_context_binding
            or request.is_knowledge_query
        )

    def _coerce_memory_anchor(self, payload: object) -> MemoryAnchor | None:
        if isinstance(payload, MemoryAnchor):
            return payload
        if not isinstance(payload, dict):
            return None
        return MemoryAnchor(
            memory_type=str(payload.get("memory_type") or "unknown"),
            source=str(payload.get("source") or ""),
            source_session_id=str(payload.get("source_session_id") or "").strip() or None,
            anchor_key=str(payload.get("anchor_key") or payload.get("anchor_id") or "").strip() or None,
            can_hydrate_context=bool(payload.get("can_hydrate_context", payload.get("source_session_id"))),
        )

    def _project_hydrated_messages(self, hydrated_entries: list[dict[str, object]]) -> list[dict[str, str]]:
        projected: list[dict[str, str]] = []
        for entry in hydrated_entries:
            content = str(entry.get("content") or "").strip()
            if not content:
                continue
            projected.append(
                {
                    "role": str(entry.get("role") or "assistant"),
                    "content": content,
                }
            )
        return projected

    def _project_hydrated_candidates(self, hydrated_entries: list[dict[str, object]]) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        for index, entry in enumerate(hydrated_entries, start=1):
            content = str(entry.get("content") or "").strip()
            if not content:
                continue
            role = str(entry.get("role") or "assistant").strip() or "assistant"
            object_id = str(entry.get("id") or f"hydrated_memory_{index}").strip()
            candidates.append(
                {
                    "object_id": f"hydrated:{object_id}",
                    "object_type": "question_object" if role == "user" else "answer_unit",
                    "content": content,
                    "source_power": "memory_anchor_hydrate",
                    "source_kind": "memory_anchor_hydrate",
                    "refs": [
                        str(item)
                        for item in (
                            entry.get("session_id"),
                            entry.get("id"),
                        )
                        if item
                    ],
                    "structured_payload": {
                        "role": role,
                        "entry_type": str(entry.get("entry_type") or "normal"),
                        "source_session_id": str(entry.get("session_id") or ""),
                    },
                }
            )
        return candidates
