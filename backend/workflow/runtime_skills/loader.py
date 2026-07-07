from __future__ import annotations

from pathlib import Path

import yaml

from workflow.runtime_skills.contracts import RuntimeSkillFallback, RuntimeSkillReference, RuntimeSkillSpec
from workflow.runtime_skills.registry import RuntimeSkillRegistry


class RuntimeSkillLoader:
    """Load Codex-style runtime skill bundles from the workflow workspace."""

    def __init__(self, *, registry: RuntimeSkillRegistry | None = None, root_dir: Path | None = None) -> None:
        self.registry = registry or RuntimeSkillRegistry()
        self.root_dir = root_dir or Path(__file__).resolve().parent

    def load(self, skill_name: str) -> RuntimeSkillSpec:
        skill_dir = self.root_dir / skill_name
        if not skill_dir.exists():
            raise FileNotFoundError(f"runtime skill not found: {skill_name}")
        skill_markdown = self._read_required_text(skill_dir / "SKILL.md")
        runtime_config = self._read_runtime_yaml(skill_dir / "runtime.yaml")
        spec = RuntimeSkillSpec(
            name=str(runtime_config.get("name") or skill_name).strip(),
            capability=str(runtime_config.get("capability") or "").strip(),
            root_dir=skill_dir,
            skill_markdown=skill_markdown,
            unit_types=tuple(str(item).strip() for item in runtime_config.get("unit_types", ()) if str(item).strip()),
            allowed_tools=tuple(str(item).strip() for item in runtime_config.get("allowed_tools", ()) if str(item).strip()),
            output_schema=str(runtime_config.get("output_schema") or "").strip(),
            max_steps=int(runtime_config.get("max_steps", 0) or 0),
            allow_llm=bool(runtime_config.get("allow_llm", False)),
            allow_external_io=bool(runtime_config.get("allow_external_io", False)),
            fallback=RuntimeSkillFallback(dict(runtime_config.get("fallback", {}))),
            references=self._load_references(skill_dir / "references"),
            raw_runtime_config=runtime_config,
        )
        self._validate(spec)
        return spec

    def _validate(self, spec: RuntimeSkillSpec) -> None:
        if not spec.capability:
            raise ValueError(f"runtime skill missing capability: {spec.name}")
        if not spec.unit_types:
            raise ValueError(f"runtime skill missing unit_types: {spec.name}")
        if not spec.allowed_tools:
            raise ValueError(f"runtime skill missing allowed_tools: {spec.name}")
        if not spec.output_schema:
            raise ValueError(f"runtime skill missing output_schema: {spec.name}")
        if spec.max_steps <= 0:
            raise ValueError(f"runtime skill max_steps must be positive: {spec.name}")
        unknown_tools = [tool_name for tool_name in spec.allowed_tools if not self.registry.has_tool(tool_name)]
        if unknown_tools:
            raise ValueError(f"runtime skill has unknown allowed tools: {', '.join(unknown_tools)}")
        if not self.registry.has_output_schema(spec.output_schema):
            raise ValueError(f"runtime skill has unknown output schema: {spec.output_schema}")

    def _read_required_text(self, path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"missing runtime skill file: {path}")
        return path.read_text(encoding="utf-8").strip()

    def _read_runtime_yaml(self, path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"missing runtime skill file: {path}")
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"runtime skill config must be a mapping: {path}")
        return dict(payload)

    def _load_references(self, references_dir: Path) -> tuple[RuntimeSkillReference, ...]:
        if not references_dir.exists():
            return ()
        references = []
        for path in sorted(references_dir.glob("*.md")):
            references.append(
                RuntimeSkillReference(
                    name=path.name,
                    path=path,
                    content=path.read_text(encoding="utf-8").strip(),
                )
            )
        return tuple(references)
