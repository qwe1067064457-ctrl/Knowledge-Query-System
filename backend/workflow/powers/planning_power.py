from __future__ import annotations

from typing import Any

from workflow.helpers.plan_format_helper import PlanFormatHelper
from workflow.types import GlobalBindingFrame, PlanBundle


class PlanningPower:
    def __init__(self, format_helper: PlanFormatHelper | None = None) -> None:
        self.format_helper = format_helper or PlanFormatHelper()

    def build_plan_bundle(
        self,
        *,
        query: str,
        task_shape: str,
        task_topology: str,
        query_units: list[dict[str, Any]] | None = None,
        bound_targets: list[dict[str, Any]] | None = None,
        global_binding_frame: GlobalBindingFrame | dict[str, Any] | None = None,
        binding_enabled: bool = False,
        recent_messages_truncated: list[dict[str, Any]] | None = None,
        recent_messages_summary: list[dict[str, Any]] | None = None,
        working_memory_hints: list[dict[str, Any]] | None = None,
        memory_anchor_hints: list[dict[str, Any]] | None = None,
        llm_call: Any | None = None,
        base_dir: Any | None = None,
        planner_worker: Any | None = None,
    ) -> dict[str, Any]:
        return self.build_plan_bundle_obj(
            query=query,
            task_shape=task_shape,
            task_topology=task_topology,
            query_units=query_units,
            bound_targets=bound_targets,
            global_binding_frame=global_binding_frame,
            binding_enabled=binding_enabled,
            recent_messages_truncated=recent_messages_truncated,
            recent_messages_summary=recent_messages_summary,
            working_memory_hints=working_memory_hints,
            memory_anchor_hints=memory_anchor_hints,
            llm_call=llm_call,
            base_dir=base_dir,
            planner_worker=planner_worker,
        ).to_dict()

    def build_plan_bundle_obj(
        self,
        *,
        query: str,
        task_shape: str,
        task_topology: str,
        query_units: list[dict[str, Any]] | None = None,
        bound_targets: list[dict[str, Any]] | None = None,
        global_binding_frame: GlobalBindingFrame | dict[str, Any] | None = None,
        binding_enabled: bool = False,
        recent_messages_truncated: list[dict[str, Any]] | None = None,
        recent_messages_summary: list[dict[str, Any]] | None = None,
        working_memory_hints: list[dict[str, Any]] | None = None,
        memory_anchor_hints: list[dict[str, Any]] | None = None,
        llm_call: Any | None = None,
        base_dir: Any | None = None,
        planner_worker: Any | None = None,
    ) -> PlanBundle:
        task_frame = self.normalize_task_frame(
            query=query,
            task_shape=task_shape,
            task_topology=task_topology,
            query_units=query_units,
            bound_targets=bound_targets,
            global_binding_frame=global_binding_frame,
            binding_enabled=binding_enabled,
            recent_messages_truncated=recent_messages_truncated,
            recent_messages_summary=recent_messages_summary,
            working_memory_hints=working_memory_hints,
            memory_anchor_hints=memory_anchor_hints,
            llm_call=llm_call,
            base_dir=base_dir,
        )
        if planner_worker is None:
            return self._fallback_bundle(task_frame, issues=["missing_planner_worker"])

        draft_plan = PlanBundle.from_dict(planner_worker.draft_plan(task_frame=task_frame))
        issues = self.validate_plan(task_frame=task_frame, plan_bundle=draft_plan)
        if not issues:
            return self._finalize_bundle(task_frame=task_frame, plan_bundle=draft_plan, refined=False)

        refined_plan = PlanBundle.from_dict(planner_worker.refine_plan(
            task_frame=task_frame,
            draft_plan=draft_plan.to_dict(),
            issues=issues,
        ))
        remaining_issues = self.validate_plan(task_frame=task_frame, plan_bundle=refined_plan)
        if remaining_issues:
            return self._fallback_bundle(task_frame, issues=remaining_issues)

        return self._finalize_bundle(task_frame=task_frame, plan_bundle=refined_plan, refined=True)

    def normalize_task_frame(
        self,
        *,
        query: str,
        task_shape: str,
        task_topology: str,
        query_units: list[dict[str, Any]] | None = None,
        bound_targets: list[dict[str, Any]] | None = None,
        global_binding_frame: GlobalBindingFrame | dict[str, Any] | None = None,
        binding_enabled: bool = False,
        recent_messages_truncated: list[dict[str, Any]] | None = None,
        recent_messages_summary: list[dict[str, Any]] | None = None,
        working_memory_hints: list[dict[str, Any]] | None = None,
        memory_anchor_hints: list[dict[str, Any]] | None = None,
        llm_call: Any | None = None,
        base_dir: Any | None = None,
    ) -> dict[str, Any]:
        frame = (
            global_binding_frame
            if isinstance(global_binding_frame, GlobalBindingFrame)
            else GlobalBindingFrame.from_dict(dict(global_binding_frame or {}))
        )
        truncated_messages = (
            list(recent_messages_truncated or ())
            if recent_messages_truncated is not None
            else list(recent_messages_summary or ())
        )
        return {
            "goal": query,
            "task_shape": task_shape,
            "task_topology": task_topology,
            "query_units": list(query_units or ()),
            "bound_targets": list(bound_targets or ()),
            "global_binding_frame": frame.to_dict(),
            "binding_enabled": binding_enabled,
            "recent_messages_truncated": truncated_messages,
            "recent_messages_summary": truncated_messages,
            "working_memory_hints": list(working_memory_hints or ()),
            "llm_call": llm_call,
            "base_dir": base_dir,
            "planning_mode_hint": self._resolve_planning_mode(task_shape=task_shape, task_topology=task_topology, query_units=query_units),
        }

    def validate_plan(self, *, task_frame: dict[str, Any], plan_bundle: PlanBundle | dict[str, Any]) -> list[str]:
        bundle = plan_bundle if isinstance(plan_bundle, PlanBundle) else PlanBundle.from_dict(plan_bundle)
        issues: list[str] = []
        ordered_steps = list(bundle.ordered_steps)
        titles = {str(step.get("title", "")) for step in ordered_steps}
        checkpoint_ids = {str(item.get("checkpoint_id", "")) for item in bundle.execution_checkpoints}
        comparison_units = list(bundle.comparison_units)
        bound_target_refs = list(bundle.bound_target_refs)
        execution_graph = bundle.execution_graph_obj()

        if task_frame.get("query_units") and not (
            "Handle each query unit explicitly" in titles or "Refine coverage for every query unit" in titles
        ):
            issues.append("missing_query_units")
        if task_frame.get("query_units") and not (
            "checkpoint_units" in checkpoint_ids or "checkpoint_units_refined" in checkpoint_ids
        ):
            issues.append("missing_query_unit_checkpoint")

        if task_frame.get("bound_targets") and not bound_target_refs:
            issues.append("missing_bound_targets")

        if task_frame.get("task_topology") == "staged" and not (
            "Preserve stage dependencies" in titles or "Restore stage dependency handling" in titles
        ):
            issues.append("missing_stage_dependency")

        if task_frame.get("task_shape") == "compare":
            if not comparison_units:
                issues.append("missing_compare_coverage")
            if not any(
                title in {"Compare targets and dimensions", "Restore symmetric comparison coverage"}
                for title in titles
            ):
                issues.append("missing_compare_step")
        if execution_graph.unit_objs() and not execution_graph.is_dag():
            issues.append("execution_graph_cycle")

        return list(dict.fromkeys(issues))

    def _resolve_planning_mode(
        self,
        *,
        task_shape: str,
        task_topology: str,
        query_units: list[dict[str, Any]] | None,
    ) -> str:
        if task_topology == "staged":
            return "staged"
        if task_shape == "compare":
            return "compare"
        if query_units:
            return "parallel_queries"
        return "structured"

    def _finalize_bundle(
        self,
        *,
        task_frame: dict[str, Any],
        plan_bundle: PlanBundle | dict[str, Any],
        refined: bool,
    ) -> PlanBundle:
        bundle = plan_bundle.to_dict() if isinstance(plan_bundle, PlanBundle) else dict(plan_bundle)
        bundle.setdefault("goal", task_frame["goal"])
        bundle.setdefault("task_shape", task_frame["task_shape"])
        bundle.setdefault("task_topology", task_frame["task_topology"])
        bundle.setdefault("planning_mode", task_frame["planning_mode_hint"])
        bundle.setdefault("comparison_units", [])
        bundle.setdefault("execution_checkpoints", [])
        bundle.setdefault("bound_target_refs", [])
        bundle.setdefault("execution_graph", {"units": [], "edges": [], "execution_summary": {"dag": True}})
        bundle["refined"] = refined
        bundle["fallback_used"] = False
        return PlanBundle.from_dict(self.format_helper.normalize_bundle(bundle))

    def _fallback_bundle(self, task_frame: dict[str, Any], *, issues: list[str]) -> PlanBundle:
        return PlanBundle.from_dict(self.format_helper.normalize_bundle(
            {
            "goal": task_frame["goal"],
            "task_shape": task_frame["task_shape"],
            "task_topology": task_frame["task_topology"],
            "planning_mode": "fallback",
            "ordered_steps": [
                {"step_id": "step_frame", "title": "Clarify execution structure", "status": "planned"},
                {"step_id": "step_answer", "title": "Produce structured answer", "status": "planned"},
            ],
            "comparison_units": [],
            "execution_checkpoints": [],
            "bound_target_refs": [],
            "execution_graph": {"units": [], "edges": [], "execution_summary": {"dag": True}},
            "fallback_reason": list(issues),
            "refined": False,
            "fallback_used": True,
            }
        ))
