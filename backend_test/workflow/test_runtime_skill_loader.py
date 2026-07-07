from __future__ import annotations

from pathlib import Path

import pytest

from workflow.orchestrated.execution_layer.executors.compare_executor import CompareExecutor
from workflow.orchestrated.execution_layer.executors.verify_executor import VerifyExecutor
from workflow.orchestrated.execution_layer.workers.base import BaseWorker
from workflow.orchestrated.execution_layer.workers.registry import WorkerRegistry
from workflow.runtime_skills.loader import RuntimeSkillLoader


class _EchoWorker(BaseWorker):
    name = "candidate_collection"
    description = "Echo payload for runtime skill tests."

    def run(self, value: str = ""):
        return {"value": value}


class _RewriteWorker(BaseWorker):
    name = "query_rewrite"
    description = "Rewrite payload for runtime skill tests."

    def run(self, query: str = ""):
        return {"query": query}


def _write_skill_bundle(
    root: Path,
    *,
    skill_name: str,
    runtime_yaml: str,
    skill_markdown: str = "# Skill\n",
) -> Path:
    skill_dir = root / skill_name
    references_dir = skill_dir / "references"
    references_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_markdown, encoding="utf-8")
    (skill_dir / "runtime.yaml").write_text(runtime_yaml, encoding="utf-8")
    (references_dir / "schema.md").write_text("# schema\n", encoding="utf-8")
    return skill_dir


def test_runtime_skill_loader_loads_bundle_and_binds_allowed_tools() -> None:
    loader = RuntimeSkillLoader()

    spec = loader.load("context-binding")

    assert spec.name == "context-binding"
    assert spec.output_schema == "ContextBindingSkillResult"
    assert spec.allowed_tools == ("candidate_collection", "query_rewrite")
    assert spec.references

    registry = WorkerRegistry()
    registry.register(_EchoWorker())
    registry.register(_RewriteWorker())
    scoped_registry = spec.bind_allowed_tools(registry)
    assert scoped_registry.names() == ("candidate_collection", "query_rewrite")


def test_runtime_skill_loader_rejects_missing_output_schema(tmp_path: Path) -> None:
    _write_skill_bundle(
        tmp_path,
        skill_name="broken-skill",
        runtime_yaml=(
            "name: broken-skill\n"
            "capability: context_binding\n"
            "unit_types:\n"
            "  - qa_like\n"
            "allowed_tools:\n"
            "  - candidate_collection\n"
            "max_steps: 3\n"
            "allow_llm: true\n"
            "allow_external_io: false\n"
        ),
    )
    loader = RuntimeSkillLoader(root_dir=tmp_path)

    with pytest.raises(ValueError, match="missing output_schema"):
        loader.load("broken-skill")


def test_runtime_skill_loader_rejects_unknown_allowed_tool(tmp_path: Path) -> None:
    _write_skill_bundle(
        tmp_path,
        skill_name="broken-tool-skill",
        runtime_yaml=(
            "name: broken-tool-skill\n"
            "capability: challenge_review\n"
            "unit_types:\n"
            "  - verify\n"
            "allowed_tools:\n"
            "  - target_resolution\n"
            "output_schema: ChallengeSkillResult\n"
            "max_steps: 4\n"
            "allow_llm: true\n"
            "allow_external_io: false\n"
        ),
    )
    loader = RuntimeSkillLoader(root_dir=tmp_path)

    with pytest.raises(ValueError, match="unknown allowed tools"):
        loader.load("broken-tool-skill")


def test_react_executor_tool_lists_do_not_expose_semantic_judges() -> None:
    verify_tools = set(VerifyExecutor.worker_names)
    compare_tools = set(CompareExecutor.worker_names)

    assert "target_resolution" not in verify_tools
    assert "target_evidence_check" not in verify_tools
    assert "challenge_re_evaluate" not in verify_tools
    assert "target_evidence_check" not in compare_tools
    assert "challenge_re_evaluate" not in compare_tools
