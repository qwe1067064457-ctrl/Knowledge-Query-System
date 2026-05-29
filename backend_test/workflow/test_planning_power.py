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
    summary_view = bundle.summary_view()

    assert bundle.planning_mode == "compare"
    assert bundle.fallback_used is False
    assert summary_view.planning_mode == "compare"
    assert summary_view.step_count == len(bundle.ordered_steps)
    assert payload["plan_summary"]["planning_mode"] == "compare"
    assert payload["bound_target_refs"] == ["compare_1"]


def test_planning_power_accepts_model_generated_execution_graph() -> None:
    power = PlanningPower()

    def llm_call(prompt: str) -> str:
        assert "prefer_minimal_graph" in prompt
        return """
        {
          "units": [
            {
              "unit_id": "unit_primary",
              "goal": "先判断是否要改schema",
              "capability": "verify",
              "depends_on": [],
              "proceed_if": null,
              "output_slot": "verify_result",
              "binding_mode": "skip",
              "retrieval_mode": "auto",
              "stop_when": "primary_stage_completed",
              "notes": ["llm_planner"]
            },
            {
              "unit_id": "unit_synthesis",
              "goal": "如果需要改schema，再总结影响接口",
              "capability": "synthesis",
              "depends_on": ["unit_primary"],
              "proceed_if": "all_dependencies_completed",
              "output_slot": "final_answer",
              "binding_mode": "skip",
              "retrieval_mode": "skip",
              "stop_when": null,
              "notes": []
            }
          ],
          "edges": [
            {
              "from_unit_id": "unit_primary",
              "to_unit_id": "unit_synthesis",
              "edge_type": "conditional",
              "condition": "all_dependencies_completed"
            }
          ],
          "graph_notes": ["llm_graph"]
        }
        """

    bundle = power.build_plan_bundle_obj(
        query="先判断是否要改schema，如果要改，再分析影响接口",
        task_shape="verify",
        task_topology="staged",
        global_binding_frame={},
        binding_enabled=False,
        recent_messages_summary=[{"role": "user", "content": "我们在讨论schema调整。"}],
        llm_call=llm_call,
        planner_worker=PlannerWorker(),
    )

    graph = bundle.execution_graph_obj()
    assert graph.is_dag() is True
    assert graph.graph_notes == ("llm_graph",)
    assert bundle.planning_mode == "staged"


def test_planning_power_falls_back_to_rule_graph_when_model_output_invalid() -> None:
    power = PlanningPower()

    def broken_llm_call(prompt: str) -> str:
        del prompt
        return """{"units": [], "edges": [], "graph_notes": ["broken"]}"""

    bundle = power.build_plan_bundle_obj(
        query="比较A和B，再分别说明两者风险。",
        task_shape="compare",
        task_topology="parallel_queries",
        query_units=[{"unit_id": "q1", "text": "比较A和B", "origin": "primary"}],
        bound_targets=[{"object_id": "compare_1", "content": "A vs B"}],
        llm_call=broken_llm_call,
        planner_worker=PlannerWorker(),
    )

    graph = bundle.execution_graph_obj()
    assert graph.unit_objs()
    assert graph.is_dag() is True
    assert bundle.fallback_used is False


def test_planning_power_falls_back_when_model_graph_has_invalid_capability_and_empty_output_slot() -> None:
    power = PlanningPower()

    def broken_llm_call(prompt: str) -> str:
        assert "不要把 unit 拆得过碎" in prompt
        return """
        {
          "units": [
            {
              "unit_id": "unit_primary",
              "goal": "先比较A和B",
              "capability": "unsupported_capability",
              "depends_on": [],
              "proceed_if": null,
              "output_slot": "",
              "binding_mode": "skip",
              "retrieval_mode": "auto",
              "stop_when": null,
              "notes": []
            }
          ],
          "edges": [],
          "graph_notes": ["broken"]
        }
        """

    bundle = power.build_plan_bundle_obj(
        query="比较A和B，再分别说明两者风险。",
        task_shape="compare",
        task_topology="parallel_queries",
        query_units=[{"unit_id": "q1", "text": "比较A和B", "origin": "primary"}],
        llm_call=broken_llm_call,
        planner_worker=PlannerWorker(),
    )

    graph = bundle.execution_graph_obj()
    assert graph.unit_objs()
    assert graph.is_dag() is True
    assert all(unit.capability in {"qa_like", "chat_like", "reject_like", "compare", "verify", "synthesis"} for unit in graph.unit_objs())
    assert all(unit.output_slot for unit in graph.unit_objs())
