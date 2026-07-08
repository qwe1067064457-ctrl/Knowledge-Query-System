from __future__ import annotations

from typing import Any

from workflow.contracts import ExecutionEdge, ExecutionGraph, ExecutionUnit, GlobalBindingFrame
from workflow.helpers.planning_prompt_helper import PlanningPromptHelper
from workflow.orchestrated.planning.grouped_unit_planner import GroupedUnitPlanner


class PlannerWorker:
    def __init__(
        self,
        *,
        prompt_helper: PlanningPromptHelper | None = None,
        grouped_planner: GroupedUnitPlanner | None = None,
    ) -> None:
        self.prompt_helper = prompt_helper or PlanningPromptHelper()
        self.grouped_planner = grouped_planner or GroupedUnitPlanner()

    def draft_plan(
        self,
        *,
        task_frame: dict[str, Any],
    ) -> dict[str, Any]:
        query = str(task_frame["goal"])
        task_shape = str(task_frame["task_shape"])
        task_topology = str(task_frame["task_topology"])
        binding_enabled = bool(task_frame.get("binding_enabled", False))
        query_units = list(task_frame.get("query_units", ()))
        bound_targets = list(task_frame.get("bound_targets", ()))
        global_binding_frame = GlobalBindingFrame.from_dict(dict(task_frame.get("global_binding_frame", {})))
        normalized_units = self._collapse_query_units(query_units)
        llm_call = task_frame.get("llm_call")
        if llm_call is not None:
            modeled = self._draft_with_llm(task_frame=task_frame, global_binding_frame=global_binding_frame, normalized_units=normalized_units)
            if modeled is not None:
                return modeled

        ordered_steps = [
            {
                "step_id": "step_frame",
                "title": "Frame execution goal and constraints",
                "status": "planned",
            },
            {
                "step_id": "step_answer",
                "title": "Produce route-aware final answer",
                "status": "planned",
            },
        ]
        comparison_units: list[dict[str, Any]] = []
        execution_checkpoints: list[dict[str, Any]] = []
        planning_mode = "structured"
        execution_graph = ExecutionGraph()

        if normalized_units:
            planning_mode = "parallel_queries"
            ordered_steps.insert(
                1,
                {
                    "step_id": "step_units",
                    "title": "Handle each query unit explicitly",
                    "status": "planned",
                },
            )
            execution_checkpoints.append(
                {
                    "checkpoint_id": "checkpoint_units",
                    "label": "Every query unit should appear in the execution plan.",
                    "status": "pending",
                }
            )
            execution_graph = self._build_parallel_graph(
                query=query,
                query_units=normalized_units,
                global_binding_frame=global_binding_frame,
                task_shape=task_shape,
                binding_enabled=binding_enabled,
            )

        if task_shape == "compare":
            planning_mode = "compare"
            comparison_units.append(
                {
                    "unit_id": "compare_primary",
                    "label": query[:80],
                    "status": "planned",
                }
            )
            ordered_steps.insert(
                1,
                {"step_id": "step_compare", "title": "Compare targets and dimensions", "status": "planned"},
            )
            execution_checkpoints.append(
                {
                    "checkpoint_id": "checkpoint_compare",
                    "label": "Both comparison sides must be covered symmetrically.",
                    "status": "pending",
                }
            )
            if not execution_graph.unit_objs():
                execution_graph = self._build_compare_graph(
                    query=query,
                    global_binding_frame=global_binding_frame,
                    binding_enabled=binding_enabled,
                )
        if task_topology == "staged":
            planning_mode = "staged"
            ordered_steps.insert(
                1,
                {"step_id": "step_stage", "title": "Preserve stage dependencies", "status": "planned"},
            )
            execution_checkpoints.append(
                {
                    "checkpoint_id": "checkpoint_stage",
                    "label": "Keep upstream results available before downstream execution.",
                    "status": "pending",
                }
            )
            execution_graph = self._build_staged_graph(
                query=query,
                global_binding_frame=global_binding_frame,
                binding_enabled=binding_enabled,
            )
        if bound_targets:
            ordered_steps.insert(
                1,
                {
                    "step_id": "step_targets",
                    "title": "Anchor execution to bound context targets",
                    "status": "planned",
                },
            )
            execution_checkpoints.append(
                {
                    "checkpoint_id": "checkpoint_targets",
                    "label": "Use the bound targets consistently across the plan.",
                    "status": "pending",
                }
            )
        if not execution_graph.unit_objs():
            execution_graph = self._build_structured_graph(
                query=query,
                global_binding_frame=global_binding_frame,
                binding_enabled=binding_enabled,
            )
        return {
            "goal": query,
            "task_shape": task_shape,
            "task_topology": task_topology,
            "planning_mode": planning_mode,
            "ordered_steps": ordered_steps,
            "comparison_units": comparison_units,
            "execution_checkpoints": execution_checkpoints,
            "bound_target_refs": [
                target.get("object_id") or target.get("content") or f"target_{index}"
                for index, target in enumerate(bound_targets, start=1)
            ],
            "execution_graph": execution_graph.to_dict(),
            "fallback_used": False,
        }

    def _draft_with_llm(
        self,
        *,
        task_frame: dict[str, Any],
        global_binding_frame: GlobalBindingFrame,
        normalized_units: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        llm_call = task_frame.get("llm_call")
        if llm_call is None:
            return None
        prompt_payload = {
            "goal": str(task_frame.get("goal") or ""),
            "task_shape": str(task_frame.get("task_shape") or ""),
            "task_topology": str(task_frame.get("task_topology") or ""),
            "query_units": normalized_units,
            "global_binding_frame": global_binding_frame.to_dict(),
            "binding_enabled": bool(task_frame.get("binding_enabled", False)),
            "recent_messages_truncated": list(
                task_frame.get("recent_messages_truncated", task_frame.get("recent_messages_summary", ())) or ()
            ),
            "working_memory_hints": list(task_frame.get("working_memory_hints", ()) or ()),
            "constraints": {
                "max_units": 6,
                "prefer_minimal_graph": True,
                "avoid_fragmented_units": True,
            },
        }
        try:
            grouped_prompt = self.prompt_helper.render_grouped_prompt(
                base_dir=task_frame.get("base_dir"),
                task_frame=prompt_payload,
            )
            grouped_plan = self.grouped_planner.parse(
                self.prompt_helper.parse_json_payload(str(llm_call(grouped_prompt))),
            )
            graph = self.grouped_planner.to_execution_graph(
                grouped_plan,
                global_binding_frame=global_binding_frame,
                binding_enabled=bool(task_frame.get("binding_enabled", False)),
            )
            unit_groups = grouped_plan.unit_group_dicts()
        except Exception:
            try:
                prompt = self.prompt_helper.render_prompt(
                    base_dir=task_frame.get("base_dir"),
                    task_frame=prompt_payload,
                )
                graph = self.prompt_helper.validate_graph_payload(
                    self.prompt_helper.parse_json_payload(str(llm_call(prompt))),
                    max_units=6,
                )
                unit_groups = ()
            except Exception:
                return None

        planning_mode = self._resolve_graph_planning_mode(
            graph=graph,
            task_shape=str(task_frame.get("task_shape") or ""),
            task_topology=str(task_frame.get("task_topology") or ""),
            normalized_units=normalized_units,
        )
        ordered_steps = [
            {"step_id": "step_frame", "title": "Frame execution goal and constraints", "status": "planned"},
            {"step_id": "step_graph", "title": "Generate execution graph from structured task frame", "status": "planned"},
            {"step_id": "step_answer", "title": "Produce route-aware final answer", "status": "planned"},
        ]
        if unit_groups:
            ordered_steps.insert(
                1,
                {"step_id": "step_grouped_units", "title": "Handle each query unit explicitly", "status": "planned"},
            )
        if planning_mode == "compare":
            ordered_steps.insert(
                1,
                {"step_id": "step_compare", "title": "Compare targets and dimensions", "status": "planned"},
            )
        execution_checkpoints = [
            {
                "checkpoint_id": "checkpoint_graph",
                "label": "Execution graph must remain a valid DAG with stable unit contracts.",
                "status": "pending",
            }
        ]
        if unit_groups:
            execution_checkpoints.append(
                {
                    "checkpoint_id": "checkpoint_units",
                    "label": "Every grouped unit should appear in the execution plan.",
                    "status": "pending",
                }
            )
        bound_targets = list(task_frame.get("bound_targets", ()))
        return {
            "goal": str(task_frame.get("goal") or ""),
            "task_shape": str(task_frame.get("task_shape") or ""),
            "task_topology": str(task_frame.get("task_topology") or ""),
            "planning_mode": planning_mode,
            "ordered_steps": ordered_steps,
            "comparison_units": (
                [{"unit_id": "compare_primary", "label": str(task_frame.get("goal") or "")[:80], "status": "planned"}]
                if planning_mode == "compare"
                else []
            ),
            "execution_checkpoints": execution_checkpoints,
            "bound_target_refs": [
                target.get("object_id") or target.get("content") or f"target_{index}"
                for index, target in enumerate(bound_targets, start=1)
            ],
            "unit_groups": unit_groups,
            "execution_graph": graph.to_dict(),
            "fallback_used": False,
            "graph_notes": list(graph.graph_notes),
        }

    def refine_plan(
        self,
        *,
        task_frame: dict[str, Any],
        draft_plan: dict[str, Any],
        issues: list[str],
    ) -> dict[str, Any]:
        plan = {
            **draft_plan,
            "ordered_steps": [dict(step) for step in draft_plan.get("ordered_steps", ())],
            "execution_checkpoints": [dict(item) for item in draft_plan.get("execution_checkpoints", ())],
            "comparison_units": [dict(item) for item in draft_plan.get("comparison_units", ())],
            "bound_target_refs": list(draft_plan.get("bound_target_refs", ())),
            "refined_from_issues": list(issues),
        }

        if "missing_query_units" in issues and task_frame.get("query_units"):
            plan["ordered_steps"].insert(
                1,
                {
                    "step_id": "step_units_refined",
                    "title": "Refine coverage for every query unit",
                    "status": "planned",
                },
            )
            plan["execution_checkpoints"].append(
                {
                    "checkpoint_id": "checkpoint_units_refined",
                    "label": "Validated every query unit after plan refinement.",
                    "status": "pending",
                }
            )
            plan["planning_mode"] = "parallel_queries"

        if "missing_bound_targets" in issues and task_frame.get("bound_targets"):
            plan["ordered_steps"].insert(
                1,
                {
                    "step_id": "step_targets_refined",
                    "title": "Re-anchor plan to bound context targets",
                    "status": "planned",
                },
            )
            plan["bound_target_refs"] = [
                target.get("object_id") or target.get("content") or f"target_{index}"
                for index, target in enumerate(task_frame.get("bound_targets", ()), start=1)
            ]
            plan["execution_checkpoints"].append(
                {
                    "checkpoint_id": "checkpoint_targets_refined",
                    "label": "Validated bound target coverage after refinement.",
                    "status": "pending",
                }
            )

        if "missing_stage_dependency" in issues and task_frame.get("task_topology") == "staged":
            plan["ordered_steps"].insert(
                1,
                {
                    "step_id": "step_stage_refined",
                    "title": "Restore stage dependency handling",
                    "status": "planned",
                },
            )
            plan["planning_mode"] = "staged"

        if "missing_compare_coverage" in issues and task_frame.get("task_shape") == "compare":
            plan["ordered_steps"].insert(
                1,
                {
                    "step_id": "step_compare_refined",
                    "title": "Restore symmetric comparison coverage",
                    "status": "planned",
                },
            )
            if not plan["comparison_units"]:
                plan["comparison_units"].append(
                    {
                        "unit_id": "compare_refined",
                        "label": str(task_frame["goal"])[:80],
                        "status": "planned",
                    }
                )
            plan["execution_checkpoints"].append(
                {
                    "checkpoint_id": "checkpoint_compare_refined",
                    "label": "Validated symmetric comparison coverage after refinement.",
                    "status": "pending",
                }
            )
            plan["planning_mode"] = "compare"

        plan["fallback_used"] = False
        return plan

    def _collapse_query_units(self, query_units: list[dict[str, Any]], *, max_units: int = 6) -> list[dict[str, Any]]:
        if len(query_units) <= max_units:
            return [dict(item) for item in query_units]
        collapsed = [dict(item) for item in query_units[: max_units - 1]]
        remaining = query_units[max_units - 1 :]
        collapsed.append(
            {
                "unit_id": "q_grouped",
                "text": "；".join(str(item.get("text", "")).strip() for item in remaining if str(item.get("text", "")).strip()),
                "origin": "primary",
                "target_refs": [],
            }
        )
        return collapsed

    def _default_binding_mode(self, frame: GlobalBindingFrame, *, binding_enabled: bool) -> str:
        if frame.recommended_binding_mode == "global_only" and len(frame.shared_target_candidates) == 1:
            return "pre_shared"
        if frame.recommended_binding_mode == "selective_per_unit":
            return "lazy"
        if binding_enabled:
            return "lazy"
        return "skip"

    def _build_parallel_graph(
        self,
        *,
        query: str,
        query_units: list[dict[str, Any]],
        global_binding_frame: GlobalBindingFrame,
        task_shape: str,
        binding_enabled: bool,
    ) -> ExecutionGraph:
        binding_mode = self._default_binding_mode(global_binding_frame, binding_enabled=binding_enabled)
        units = [
            ExecutionUnit(
                unit_id=str(item.get("unit_id") or f"unit_{index}"),
                goal=str(item.get("text") or query),
                capability="qa_like",
                output_slot=str(item.get("unit_id") or f"slot_{index}"),
                binding_mode=binding_mode,
            )
            for index, item in enumerate(query_units, start=1)
        ]
        edges: list[ExecutionEdge] = []
        synthesis_capability = "compare" if task_shape == "compare" else "synthesis"
        synthesis_unit = ExecutionUnit(
            unit_id="unit_synthesis",
            goal="Synthesize the independent branch results into one coherent answer.",
            capability=synthesis_capability,
            depends_on=tuple(unit.unit_id for unit in units),
            output_slot="final_answer",
            binding_mode="skip",
            retrieval_mode="skip",
            stop_when="dependencies_summarized",
        )
        units.append(synthesis_unit)
        edges.extend(
            ExecutionEdge(from_unit_id=unit.unit_id, to_unit_id=synthesis_unit.unit_id)
            for unit in units[:-1]
        )
        return ExecutionGraph(units=tuple(unit.to_dict() for unit in units), edges=tuple(edge.to_dict() for edge in edges))

    def _build_staged_graph(self, *, query: str, global_binding_frame: GlobalBindingFrame, binding_enabled: bool) -> ExecutionGraph:
        binding_mode = self._default_binding_mode(global_binding_frame, binding_enabled=binding_enabled)
        units = [
            ExecutionUnit(
                unit_id="unit_stage_primary",
                goal=query,
                capability="verify",
                output_slot="stage_primary",
                binding_mode=binding_mode,
                stop_when="primary_stage_completed",
            ),
            ExecutionUnit(
                unit_id="unit_stage_synthesis",
                goal="Summarize the staged execution result into the final answer.",
                capability="synthesis",
                depends_on=("unit_stage_primary",),
                proceed_if="all_dependencies_completed",
                output_slot="final_answer",
                binding_mode="skip",
                retrieval_mode="skip",
            ),
        ]
        edges = [
            ExecutionEdge(
                from_unit_id="unit_stage_primary",
                to_unit_id="unit_stage_synthesis",
                edge_type="conditional",
                condition="all_dependencies_completed",
            )
        ]
        return ExecutionGraph(units=tuple(unit.to_dict() for unit in units), edges=tuple(edge.to_dict() for edge in edges))

    def _build_compare_graph(self, *, query: str, global_binding_frame: GlobalBindingFrame, binding_enabled: bool) -> ExecutionGraph:
        binding_mode = self._default_binding_mode(global_binding_frame, binding_enabled=binding_enabled)
        units = [
            ExecutionUnit(
                unit_id="unit_compare",
                goal=query,
                capability="compare",
                output_slot="compare_result",
                binding_mode=binding_mode,
            ),
            ExecutionUnit(
                unit_id="unit_compare_synthesis",
                goal="Turn the comparison result into a route-aware final answer.",
                capability="synthesis",
                depends_on=("unit_compare",),
                proceed_if="all_dependencies_completed",
                output_slot="final_answer",
                binding_mode="skip",
                retrieval_mode="skip",
            ),
        ]
        edges = [ExecutionEdge(from_unit_id="unit_compare", to_unit_id="unit_compare_synthesis")]
        return ExecutionGraph(units=tuple(unit.to_dict() for unit in units), edges=tuple(edge.to_dict() for edge in edges))

    def _build_structured_graph(self, *, query: str, global_binding_frame: GlobalBindingFrame, binding_enabled: bool) -> ExecutionGraph:
        binding_mode = self._default_binding_mode(global_binding_frame, binding_enabled=binding_enabled)
        units = [
            ExecutionUnit(
                unit_id="unit_primary",
                goal=query,
                capability="qa_like",
                output_slot="final_answer",
                binding_mode=binding_mode,
            )
        ]
        return ExecutionGraph(units=tuple(unit.to_dict() for unit in units), edges=())

    def _resolve_graph_planning_mode(
        self,
        *,
        graph: ExecutionGraph,
        task_shape: str,
        task_topology: str,
        normalized_units: list[dict[str, Any]],
    ) -> str:
        if task_topology == "staged":
            return "staged"
        if task_shape == "compare":
            return "compare"
        if normalized_units:
            return "parallel_queries"
        if any(edge.edge_type == "conditional" for edge in graph.edge_objs()):
            return "staged"
        return "structured"
