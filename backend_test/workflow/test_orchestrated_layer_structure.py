from __future__ import annotations

from pathlib import Path

from workflow.helpers.global_binding_prompt_helper import GlobalBindingPromptHelper
from workflow.helpers.planning_prompt_helper import PlanningPromptHelper
from workflow.orchestrated.answer_layer.projectors.answer_layer_projector import build_answer_assembly_package
from workflow.orchestrated.execution_layer.engine.execution_layer import ExecutionLayer
from workflow.orchestrated.route.orchestrated_runner import OrchestratedRouteRunner
from workflow.types import ExecutionPayload


def test_orchestrated_owner_imports_resolve() -> None:
    runner = OrchestratedRouteRunner()
    assert runner.route_name == "orchestrated"
    assert isinstance(runner.execution_layer, ExecutionLayer)


def test_orchestrated_readmes_capture_responsibility_and_essence() -> None:
    root = Path("backend/workflow/orchestrated")
    readmes = [
        root / "README.md",
        root / "route" / "README.md",
        root / "binding" / "README.md",
        root / "planning" / "README.md",
        root / "execution_layer" / "README.md",
        root / "answer_layer" / "README.md",
    ]
    for path in readmes:
        content = path.read_text(encoding="utf-8")
        assert "职责" in content
        assert "本质作用" in content
    execution_readme = (root / "execution_layer" / "README.md").read_text(encoding="utf-8")
    answer_readme = (root / "answer_layer" / "README.md").read_text(encoding="utf-8")
    assert "不放什么" in execution_readme
    assert "不放什么" in answer_readme


def test_prompt_helpers_prefer_owner_prompt_paths(tmp_path: Path) -> None:
    base_dir = tmp_path / "backend"
    new_binding = base_dir / "workflow" / "orchestrated" / "binding" / "prompts"
    new_planning = base_dir / "workflow" / "orchestrated" / "planning" / "prompts"
    old_prompt_dir = base_dir / "prompts" / "workflow"
    new_binding.mkdir(parents=True)
    new_planning.mkdir(parents=True)
    old_prompt_dir.mkdir(parents=True)

    (old_prompt_dir / "global_binding_frame_prompt.md").write_text("old-binding", encoding="utf-8")
    (old_prompt_dir / "execution_graph_planner_prompt.md").write_text("old-planning", encoding="utf-8")
    (new_binding / "global_binding_frame_prompt.md").write_text("new-binding", encoding="utf-8")
    (new_planning / "execution_graph_planner_prompt.md").write_text("new-planning", encoding="utf-8")

    assert GlobalBindingPromptHelper().load_prompt(base_dir) == "new-binding"
    assert PlanningPromptHelper().load_prompt(base_dir) == "new-planning"


def test_prompt_helpers_fall_back_to_legacy_paths(tmp_path: Path) -> None:
    base_dir = tmp_path / "backend"
    old_prompt_dir = base_dir / "prompts" / "workflow"
    old_prompt_dir.mkdir(parents=True)
    (old_prompt_dir / "global_binding_frame_prompt.md").write_text("old-binding", encoding="utf-8")
    (old_prompt_dir / "execution_graph_planner_prompt.md").write_text("old-planning", encoding="utf-8")

    assert GlobalBindingPromptHelper().load_prompt(base_dir) == "old-binding"
    assert PlanningPromptHelper().load_prompt(base_dir) == "old-planning"


def test_answer_layer_package_preserves_execution_states() -> None:
    payload = ExecutionPayload(
        route="orchestrated",
        handling_mode="normal",
        action="agent",
        plan_bundle={
            "goal": "示例问题",
            "planning_mode": "staged",
            "unit_results": [
                {"unit_id": "u1", "capability": "verify", "state": "completed", "output_slot": "decision"},
                {"unit_id": "u2", "capability": "qa_like", "state": "degraded", "output_slot": "plan"},
                {"unit_id": "u3", "capability": "synthesis", "state": "completed", "output_slot": "final_answer"},
            ],
        },
        answer_constraints={"must_acknowledge_uncertainty": True},
        key_events=("retrieval_quality_weak",),
    )

    package = build_answer_assembly_package(question="示例问题", payload=payload)

    assert package.execution_summary["completed"] == ["u1", "u3"]
    assert package.execution_summary["degraded"] == ["u2"]
    assert any(item.role == "primary" for item in package.main_findings)
