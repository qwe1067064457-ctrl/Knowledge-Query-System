from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import StructuredTool

from workflow.orchestrated.execution_layer.workers.base import BaseWorker, WorkerSpec


def _json_default(value: Any):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return str(value)


@dataclass(frozen=True)
class WorkerRegistryEntry:
    name: str
    description: str
    callable: Any


class WorkerRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, WorkerRegistryEntry] = {}

    def register(self, worker: BaseWorker | WorkerSpec) -> None:
        spec = worker.as_spec() if isinstance(worker, BaseWorker) else worker
        self._entries[spec.name] = WorkerRegistryEntry(
            name=spec.name,
            description=spec.description,
            callable=spec.callable,
        )

    def get(self, name: str):
        return self._entries[name].callable

    def has(self, name: str) -> bool:
        return name in self._entries

    def names(self) -> tuple[str, ...]:
        return tuple(self._entries.keys())

    def build_langchain_tools(self, names: list[str] | tuple[str, ...]):
        tools: list[StructuredTool] = []
        for name in names:
            if name not in self._entries:
                continue
            entry = self._entries[name]

            def _invoke(payload_json: str, *, _callable=entry.callable):
                payload = json.loads(payload_json) if payload_json.strip() else {}
                result = _callable(**payload)
                return json.dumps(result, ensure_ascii=False, default=_json_default)

            tools.append(
                StructuredTool.from_function(
                    func=_invoke,
                    name=entry.name,
                    description=entry.description,
                )
            )
        return tools

