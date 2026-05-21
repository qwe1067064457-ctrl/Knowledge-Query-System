from __future__ import annotations

from workflow.powers.planning_power import PlanningPower
from workflow.workers.planner_worker import PlannerWorker


class _BrokenPlannerWorker:
    def draft_plan(self, *, task_frame: dict[str, object]) -> dict[str, object]:
        return {
            "goal": task_frame["goal"],
            "task_shape": task_frame["task_shape"],
            "task_topology": task_frame["task_topology"],
            "planning_mode": "structured",
            "ordered_steps": [
                {"step_id": "step_frame", "title": "Frame execution goal and constraints", "status": "planned"},
                {"step_id": "step_answer", "title": "Produce route-aware final answer", "status": "planned"},
            ],
            "comparison_units": [],
            "execution_checkpoints": [],
            "bound_target_refs": [],
            "fallback_used": False,
        }

    def refine_plan(
        self,
        *,
        task_frame: dict[str, object],
        draft_plan: dict[str, object],
        issues: list[str],
    ) -> dict[str, object]:
        return dict(draft_plan)


def test_planning_power_returns_refined_structured_bundle() -> None:
    power = PlanningPower()

    bundle = power.build_plan_bundle(
        query="比较A和B，再分别说明两者风险。",
        task_shape="compare",
        task_topology="parallel_queries",
        query_units=[
            {"unit_id": "q1", "text": "比较A和B", "origin": "primary"},
            {"unit_id": "q2", "text": "说明两者风险", "origin": "support"},
        ],
        bound_targets=[{"object_id": "compare_1", "content": "A vs B"}],
        planner_worker=PlannerWorker(),
    )

    assert bundle["fallback_used"] is False
    assert bundle["planning_mode"] == "compare"
    assert bundle["execution_checkpoints"]
    assert bundle["bound_target_refs"] == ["compare_1"]
    assert bundle["format_helper_applied"] is True
    assert bundle["ordered_steps"][0]["sequence"] == 1
    assert bundle["plan_summary"]["planning_mode"] == "compare"
    assert bundle["plan_summary"]["step_count"] == len(bundle["ordered_steps"])
    assert bundle["plan_summary"]["fallback_used"] is False


def test_planning_power_falls_back_when_refinement_still_invalid() -> None:
    power = PlanningPower()

    bundle = power.build_plan_bundle(
        query="比较A和B，再分别说明两者风险。",
        task_shape="compare",
        task_topology="parallel_queries",
        query_units=[{"unit_id": "q1", "text": "比较A和B", "origin": "primary"}],
        bound_targets=[{"object_id": "compare_1", "content": "A vs B"}],
        planner_worker=_BrokenPlannerWorker(),
    )

    assert bundle["fallback_used"] is True
    assert bundle["planning_mode"] == "fallback"
    assert bundle["fallback_reason"]
    assert bundle["format_helper_applied"] is True
    assert bundle["plan_summary"]["fallback_used"] is True
    assert bundle["plan_summary"]["fallback_reason"]


def test_planning_power_can_return_typed_plan_bundle_object() -> None:
    power = PlanningPower()

    bundle = power.build_plan_bundle_obj(
        query="比较A和B，再分别说明两者风险。",
        task_shape="compare",
        task_topology="parallel_queries",
        query_units=[{"unit_id": "q1", "text": "比较A和B", "origin": "primary"}],
        bound_targets=[{"object_id": "compare_1", "content": "A vs B"}],
        planner_worker=PlannerWorker(),
    )

    payload = bundle.to_dict()

    assert bundle.planning_mode == "compare"
    assert bundle.fallback_used is False
    assert payload["plan_summary"]["planning_mode"] == "compare"
    assert payload["bound_target_refs"] == ["compare_1"]
