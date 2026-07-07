from __future__ import annotations

from pathlib import Path

from workflow.helpers.global_binding_prompt_helper import GlobalBindingPromptHelper
from workflow.helpers.planning_prompt_helper import PlanningPromptHelper
from workflow.orchestrated.answer_layer.projectors.answer_prompt_block_builder import build_answer_prompt_blocks
from workflow.orchestrated.answer_layer.projectors.answer_layer_projector import build_answer_assembly_package
from workflow.orchestrated.execution_layer.contracts.unit_result import (
    CompareResultPayload,
    SynthesisResultPayload,
    VerifyResultPayload,
)
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
        action="respond",
        plan_bundle={
            "goal": "示例问题",
            "planning_mode": "staged",
            "unit_results": [
                {
                    "unit_id": "u1",
                    "capability": "verify",
                    "state": "completed",
                    "output_slot": "decision",
                    "result_payload": {
                        "judgment": "supported",
                        "summary": "前置判断支持继续执行。",
                        "confidence": "high",
                    },
                },
                {"unit_id": "u2", "capability": "qa_like", "state": "degraded", "output_slot": "plan"},
                {
                    "unit_id": "u3",
                    "capability": "synthesis",
                    "state": "completed",
                    "output_slot": "final_answer",
                    "result_payload": {
                        "main_conclusion": "最终建议继续推进。",
                        "supporting_points": ["前置判断支持", "方案已形成"],
                        "cautions": ["仍需控制改动范围"],
                        "confidence": "medium",
                    },
                },
            ],
        },
        answer_constraints={"must_acknowledge_uncertainty": True},
        key_events=("retrieval_quality_weak",),
    )

    package = build_answer_assembly_package(question="示例问题", payload=payload)

    assert package.execution_summary["completed"] == ["u1", "u3"]
    assert package.execution_summary["degraded"] == ["u2"]
    assert any(item.role == "primary" for item in package.main_findings)
    assert any("最终建议继续推进" in item.summary for item in package.main_findings)
    assert any(item.confidence == "low" for item in package.main_findings if item.unit_id == "u2")
    assert package.primary_findings
    assert package.supporting_findings
    assert package.answer_cautions

    blocks = build_answer_prompt_blocks(package)
    ordered_blocks = blocks.as_ordered_blocks()
    assert any("[Primary Findings]" in block for block in ordered_blocks)
    assert any("[Supporting Findings]" in block for block in ordered_blocks)
    assert any("[Status Findings]" in block for block in ordered_blocks)


def test_execution_layer_result_payload_contracts_round_trip() -> None:
    verify = VerifyResultPayload(
        judgment="supported",
        can_proceed=True,
        confidence="high",
        summary="前置判断支持继续执行。",
        key_reasons=("证据充分",),
        consumed_working_memory=("user_assertion",),
    )
    compare = CompareResultPayload(
        comparison_status="completed",
        summary="完成方案对比。",
        dimensions=("成本", "风险"),
        tradeoff=("方案A成本低",),
        confidence="medium",
        consumed_working_memory=("focus_task",),
    )
    synthesis = SynthesisResultPayload(
        main_conclusion="建议采用方案A。",
        supporting_points=("成本更低",),
        cautions=("注意边界回归",),
        final_text_draft="建议采用方案A，并注意边界回归。",
        confidence="medium",
        consumed_working_memory=("answer_unit",),
    )

    assert VerifyResultPayload.from_dict(verify.to_dict()).judgment == "supported"
    assert CompareResultPayload.from_dict(compare.to_dict()).dimensions == ("成本", "风险")
    assert SynthesisResultPayload.from_dict(synthesis.to_dict()).cautions == ("注意边界回归",)
