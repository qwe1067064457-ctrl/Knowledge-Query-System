from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain.agents import create_agent

from memory_system.session_working_memory.models import SessionWorkingMemory
from workflow.orchestrated.execution_layer.contracts.unit_execution_outcome import (
    UnitExecutionContext,
    UnitExecutionOutcome,
)
from workflow.runtime_skills.unit_runtime_config import get_unit_runtime_config, tool_names_for_unit


class BaseCapabilityExecutor:
    capability = "qa_like"
    worker_names: tuple[str, ...] = ()

    def run(
        self,
        *,
        unit_context: UnitExecutionContext,
        worker_registry,
        llm_factory=None,
        trace_hooks: dict[str, Any] | None = None,
    ) -> UnitExecutionOutcome:
        del unit_context, worker_registry, llm_factory, trace_hooks
        raise NotImplementedError

    def _entries(self, memory: SessionWorkingMemory) -> list[object]:
        entries = memory.active_entries()
        return entries or memory.entries

    def _memory_from(self, working_memory) -> SessionWorkingMemory:
        return working_memory if isinstance(working_memory, SessionWorkingMemory) else SessionWorkingMemory.from_dict(working_memory)

    def _load_prompt(self, prompt_name: str) -> str:
        path = Path(__file__).with_name("prompts") / prompt_name
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def _invoke_agent_json(
        self,
        *,
        llm_factory,
        worker_registry,
        prompt_name: str,
        worker_names: tuple[str, ...] | None = None,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        if llm_factory is None:
            return None
        config = get_unit_runtime_config(str(self.capability))
        if not config.react_enabled:
            return None
        model = llm_factory()
        selected_workers = worker_names if worker_names is not None else tool_names_for_unit(str(self.capability))
        tools = worker_registry.build_langchain_tools(list(selected_workers))
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=self._load_prompt(prompt_name),
        )
        response = agent.invoke(
            {"messages": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]}
        )
        content = response.get("messages", [])[-1].content if isinstance(response, dict) and response.get("messages") else ""
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            content = "".join(text_parts)
        if not isinstance(content, str) or not content.strip():
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    return None
        return None
