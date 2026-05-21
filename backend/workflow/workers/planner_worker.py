from __future__ import annotations

from typing import Any


class PlannerWorker:
    def draft_plan(
        self,
        *,
        task_frame: dict[str, Any],
    ) -> dict[str, Any]:
        query = str(task_frame["goal"])
        task_shape = str(task_frame["task_shape"])
        task_topology = str(task_frame["task_topology"])
        query_units = list(task_frame.get("query_units", ()))
        bound_targets = list(task_frame.get("bound_targets", ()))

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

        if query_units:
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
            "fallback_used": False,
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
