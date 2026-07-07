from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeSkillFallback:
    """Fallback routing declared by a runtime skill."""

    rules: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        return dict(self.rules)


@dataclass(frozen=True)
class RuntimeSkillReference:
    """Reference material loaded alongside the runtime work manual."""

    name: str
    path: Path
    content: str


@dataclass(frozen=True)
class RuntimeSkillSpec:
    """Normalized runtime skill contract for typed execution units."""

    name: str
    capability: str
    root_dir: Path
    skill_markdown: str
    unit_types: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    output_schema: str
    max_steps: int
    allow_llm: bool
    allow_external_io: bool
    fallback: RuntimeSkillFallback = field(default_factory=RuntimeSkillFallback)
    references: tuple[RuntimeSkillReference, ...] = ()
    raw_runtime_config: dict[str, Any] = field(default_factory=dict)

    def bind_allowed_tools(self, worker_registry) -> Any:
        """Return a worker registry narrowed to this skill's deterministic tools."""
        return worker_registry.subset(self.allowed_tools)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "capability": self.capability,
            "root_dir": str(self.root_dir),
            "unit_types": list(self.unit_types),
            "allowed_tools": list(self.allowed_tools),
            "output_schema": self.output_schema,
            "max_steps": self.max_steps,
            "allow_llm": self.allow_llm,
            "allow_external_io": self.allow_external_io,
            "fallback": self.fallback.to_dict(),
            "references": [reference.name for reference in self.references],
        }
