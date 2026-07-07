from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent

from workflow.runtime_skills.unit_runtime_config import FORBIDDEN_REACT_TOOLS, get_unit_runtime_config


@dataclass(frozen=True)
class BoundedReactAgentSpec:
    capability: str
    tool_names: tuple[str, ...]
    output_schema: str


class BoundedReactAgentFactory:
    """Build a ReAct-style agent using only the current unit's tool whitelist."""

    def spec_for(self, capability: str, *, extra_tools: tuple[str, ...] = ()) -> BoundedReactAgentSpec:
        config = get_unit_runtime_config(capability)
        tool_names = tuple(dict.fromkeys([*config.tools, *extra_tools]))
        forbidden = sorted(set(tool_names) & FORBIDDEN_REACT_TOOLS)
        if forbidden:
            raise ValueError(f"bounded react agent requested forbidden tools: {', '.join(forbidden)}")
        if not config.react_enabled:
            raise ValueError(f"unit capability does not allow react agent: {capability}")
        return BoundedReactAgentSpec(
            capability=capability,
            tool_names=tool_names,
            output_schema=config.output_schema,
        )

    def create(self, *, capability: str, llm_factory, worker_registry, system_prompt: str):
        spec = self.spec_for(capability)
        tools = worker_registry.build_langchain_tools(spec.tool_names)
        model = llm_factory()
        return create_agent(model=model, tools=tools, system_prompt=system_prompt)
