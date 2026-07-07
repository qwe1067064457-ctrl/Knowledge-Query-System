from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class OutputSchemaContract:
    """Minimal output contract metadata for runtime skill validation."""

    name: str
    required_fields: tuple[str, ...]


class RuntimeSkillRegistry:
    """Registry of allowed deterministic tools and known output schemas."""

    def __init__(
        self,
        *,
        allowed_tools: Iterable[str] | None = None,
        output_schemas: Iterable[OutputSchemaContract] | None = None,
    ) -> None:
        self._allowed_tools = set(
            allowed_tools
            or (
                "candidate_collection",
                "query_rewrite",
                "answer_constraint",
                "query_unit_builder",
                "evidence_anchor",
                "caution_assembly",
            )
        )
        schema_items = output_schemas or (
            OutputSchemaContract(
                name="ContextBindingSkillResult",
                required_fields=("status", "relevant_set", "confidence", "reason"),
            ),
            OutputSchemaContract(
                name="ChallengeSkillResult",
                required_fields=("status", "targets", "findings", "confidence", "reason"),
            ),
            OutputSchemaContract(
                name="DecompositionSkillResult",
                required_fields=("status", "query_units", "confidence", "reason"),
            ),
        )
        self._output_schemas = {schema.name: schema for schema in schema_items}

    def has_tool(self, name: str) -> bool:
        return str(name or "").strip() in self._allowed_tools

    def allowed_tools(self) -> tuple[str, ...]:
        return tuple(sorted(self._allowed_tools))

    def has_output_schema(self, name: str) -> bool:
        return str(name or "").strip() in self._output_schemas

    def output_schema(self, name: str) -> OutputSchemaContract:
        return self._output_schemas[name]
