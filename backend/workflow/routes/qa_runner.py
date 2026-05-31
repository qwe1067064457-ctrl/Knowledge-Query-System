from __future__ import annotations

from dataclasses import replace

from context.session import DEFAULT_AGENT
from memory_system.memory_anchor import MemoryAnchor
from workflow.powers.challenge_power import ChallengePower
from workflow.powers.context_binding_power import ContextBindingPower
from workflow.powers.retrieval_power import RetrievalPower
from workflow.retrieval_gate import RetrievalGate
from workflow.orchestrated.execution_layer.adapters.retrieval_adapter import build_retrieval_workers
from workflow.orchestrated.execution_layer.adapters.review_adapter import build_review_workers
from workflow.orchestrated.execution_layer.workers.registry import WorkerRegistry
from workflow.routes.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import ContextBindingResult, QueryUnit, WorkflowPlan
from workflow.workers.binding_worker import BindingWorker
from workflow.workers.memory_anchor_worker import MemoryAnchorWorker
from workflow.workers.review_worker import ReviewWorker


def _merge_key_events(*event_groups: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in event_groups:
        for item in group:
            if item and item not in merged:
                merged.append(str(item))
    return tuple(merged)


def _binding_events(binding: ContextBindingResult | None) -> tuple[str, ...]:
    if binding is None:
        return ()
    return ("binding_ambiguous",) if binding.binding_ambiguous else ("binding_applied",)


def _retrieval_events(*, retrieval_quality: dict[str, object], repaired_units: int, missing_evidence: bool) -> tuple[str, ...]:
    events = ["retrieval_performed"]
    if repaired_units > 0:
        events.append("retrieval_repaired")
    if missing_evidence or retrieval_quality.get("status") == "bad":
        events.append("retrieval_quality_weak")
    return tuple(events)


def _challenge_events(challenge) -> tuple[str, ...]:
    events: list[str] = []
    if challenge.follow_up_retrieval_attempted():
        events.append("follow_up_retrieval_attempted")
    if challenge.review_bundle_obj().follow_up_retrieval_improved():
        events.append("follow_up_retrieval_improved")
    if challenge.status == "needs_clarification":
        events.append("clarification_required")
    if challenge.status == "insufficient_evidence":
        events.append("insufficient_evidence")
    return tuple(events)


class QaRouteRunner(BaseRouteRunner):
    route_name = "qa"

    def __init__(self) -> None:
        self.binding_worker = BindingWorker()
        self.review_worker = ReviewWorker()
        self.memory_anchor_worker = MemoryAnchorWorker()
        self.context_binding_power = ContextBindingPower(binding_worker=self.binding_worker)
        self.retrieval_power = RetrievalPower()
        self.challenge_power = ChallengePower()
        self.retrieval_gate = RetrievalGate()

    def _build_worker_registry(self) -> WorkerRegistry:
        registry = WorkerRegistry()
        for worker in build_retrieval_workers(
            retrieval_power=self.retrieval_power,
            review_worker=self.review_worker,
        ):
            registry.register(worker)
        for worker in build_review_workers(review_worker=self.review_worker):
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
        recent_messages, hydrated_candidates, memory_anchor_count, hydrated_memory_entry_count = self._prepare_memory_anchor_context(
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

        binding_result: ContextBindingResult | None = None
        binding_candidates = [*self._registry_binding_candidates(request), *hydrated_candidates]
        if "context_binding_power" in plan.enabled_powers:
            candidate_entries = self.context_binding_power.collect_candidates(binding_candidates)
            binding_result = self.context_binding_power.bind(
                request.message,
                candidate_entries,
                working_memory=request.context.get("working_memory"),
                recent_messages=recent_messages,
                llm_call=request.context.get("bound_query_llm_call"),
                base_dir=request.context.get("base_dir"),
                rewrite_query=bool(plan.rewrite_query),
                recent_power=request.context.get("recent_power"),
                recent_object_type=request.context.get("recent_object_type"),
                memory_anchors=request.context.get("memory_anchors"),
            )
            key_events = _merge_key_events(
                key_events,
                _binding_events(binding_result),
            )
            context_bundle = replace(
                context_bundle,
                binding=binding_result,
                binding_summary=binding_result.binding_summary or "binding_applied",
                candidate_count=len(candidate_entries),
            )
        context_bundle = self._normalize_context_bundle_obj(plan, context_bundle)

        evidence_bundle = payload.evidence_bundle
        evidence_candidates = list(self._registry_evidence_candidates(request))
        retrieval_decision = self.retrieval_gate.decide(
            plan=plan,
            request=request,
            binding_result=binding_result,
        )
        if "retrieval_power" in plan.enabled_powers and retrieval_decision.should_retrieve:
            target_refs = binding_result.target_refs() if binding_result is not None else ()
            query_units = (
                QueryUnit(
                    unit_id="primary",
                    text=(binding_result.rewritten_query if binding_result is not None and binding_result.rewritten_query else request.message).strip(),
                    origin="primary",
                    target_refs=target_refs,
                ),
            )
            evidence_bundle = self.retrieval_power.retrieve(query_units)
            seen = {candidate.object_id for candidate in evidence_candidates}
            for candidate in evidence_bundle.to_evidence_ref_candidate_objs():
                if candidate.object_id in seen:
                    continue
                seen.add(candidate.object_id)
                evidence_candidates.append(candidate)
            retrieval_quality = self.review_worker.retrieval_quality_check(evidence_bundle=evidence_bundle)
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

        review_bundle = payload.review_bundle_obj()
        if "challenge_power" in plan.enabled_powers:
            challenge = self.challenge_power.execute(
                query=request.message,
                rewritten_query=binding_result.rewritten_query if binding_result is not None else None,
                candidate_targets=list(context_bundle.bound_targets()),
                binding_result=binding_result,
                evidence_candidates=evidence_candidates,
                binding_worker=self.binding_worker,
                review_worker=self.review_worker,
                retrieval_power=self.retrieval_power if "retrieval_power" in plan.enabled_powers else None,
                worker_registry=worker_registry,
            )
            review_bundle = self._normalize_review_bundle_obj(challenge.to_review_bundle())
            answer_constraints.update(challenge.answer_constraints)
            key_events = _merge_key_events(
                key_events,
                _challenge_events(challenge),
            )
            if challenge.status == "needs_clarification" and payload.status == "ready":
                payload = replace(payload, status="needs_clarification")

        return self._finalize_payload(
            payload,
            plan,
            context_bundle=context_bundle,
            plan_bundle=payload.plan_bundle,
            review_bundle=review_bundle,
            answer_constraints=answer_constraints,
            key_events=key_events,
            evidence_bundle=evidence_bundle,
        )

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
