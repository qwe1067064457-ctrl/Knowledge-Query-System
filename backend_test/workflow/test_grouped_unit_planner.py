from __future__ import annotations

import pytest

from workflow.orchestrated.planning.grouped_unit_planner import GroupedUnitPlanner
from workflow.orchestrated.planning.grouped_unit_contracts import grouped_plan_from_payload
from workflow.powers.planning_power import PlanningPower
from workflow.workers.planner_worker import PlannerWorker


def test_grouped_unit_planner_accepts_parallel_compare_synthesis_plan() -> None:
    plan = grouped_plan_from_payload(
        {
            "unit_groups": [
                [
                    {"id": "u1", "type": "qa_like", "query": "A 公司的 AI 专利布局情况"},
                    {"id": "u2", "type": "qa_like", "query": "B 公司的 AI 专利布局情况"},
                ],
                [{"id": "u3", "type": "compare", "query": "对比 A 公司和 B 公司在 AI 专利布局上的差异"}],
                [{"id": "u4", "type": "synthesis", "query": "汇总专利布局差异和优劣势"}],
            ]
        }
    )

    assert plan.total_units() == 4
    assert len(plan.unit_groups[0]) == 2


@pytest.mark.parametrize(
    "payload, error",
    [
        ({"unit_groups": [[{"id": "u1", "type": "planning", "query": "规划"}]]}, "invalid_capability"),
        ({"unit_groups": [[{"id": "u1", "type": "qa_like", "query": "问题"}], [{"id": "u1", "type": "synthesis", "query": "汇总"}]]}, "duplicate_unit_id"),
        ({"unit_groups": [[{"id": f"u{i}", "type": "qa_like", "query": f"问题{i}"} for i in range(11)]]}, "too_many_units"),
        ({"unit_groups": [[{"id": "u1", "type": "qa_like", "query": "A"}], [{"id": "u2", "type": "compare", "query": "比较 A"}]]}, "missing_final_synthesis"),
    ],
)
def test_grouped_unit_planner_rejects_invalid_payloads(payload, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        grouped_plan_from_payload(payload)


def test_grouped_plan_to_execution_graph_projects_cross_group_edges() -> None:
    planner = GroupedUnitPlanner()
    plan = planner.parse(
        {
            "unit_groups": [
                [
                    {"id": "u1", "type": "qa_like", "query": "A 公司 AI 专利布局"},
                    {"id": "u2", "type": "verify", "query": "B 公司是否有 AI 专利证据"},
                ],
                [{"id": "u3", "type": "synthesis", "query": "汇总分析"}],
            ]
        }
    )

    graph = planner.to_execution_graph(plan)

    assert len(graph.unit_objs()) == 3
    assert {(edge.from_unit_id, edge.to_unit_id) for edge in graph.edge_objs()} == {("u1", "u3"), ("u2", "u3")}
    assert graph.unit_objs()[0].depends_on == ()
    assert graph.unit_objs()[2].depends_on == ("u1", "u2")


def test_planning_power_accepts_model_generated_grouped_unit_plan() -> None:
    def llm_call(prompt: str) -> str:
        assert "unit_groups" in prompt
        return """
        {
          "unit_groups": [
            [
              {"id": "u1", "type": "qa_like", "query": "A 公司 AI 专利布局"},
              {"id": "u2", "type": "qa_like", "query": "B 公司 AI 专利布局"}
            ],
            [{"id": "u3", "type": "compare", "query": "比较 A 公司和 B 公司 AI 专利布局"}],
            [{"id": "u4", "type": "synthesis", "query": "汇总 AI 专利布局差异"}]
          ]
        }
        """

    bundle = PlanningPower().build_plan_bundle_obj(
        query="A 公司和 B 公司的 AI 专利布局有什么差异？哪个更有优势？",
        task_shape="compare",
        task_topology="parallel_queries",
        llm_call=llm_call,
        planner_worker=PlannerWorker(),
    )

    graph = bundle.execution_graph_obj()
    assert bundle.unit_group_dicts()[0][0]["id"] == "u1"
    assert bundle.summary_dict()["unit_group_count"] == 3
    assert bundle.summary_dict()["parallel_group_count"] == 1
    assert graph.is_dag() is True
    assert graph.graph_notes == ("grouped_unit_plan",)
