"""Memory system package."""

from __future__ import annotations

from typing import Any

__all__ = ["MemorySystem", "MemoryAnchor", "MemoryAnchorBuilder", "MemoryContextHydrator"]


def __getattr__(name: str) -> Any:
    if name == "MemorySystem":
        from memory_system.memory_service import MemorySystem

        return MemorySystem
    if name in {"MemoryAnchor", "MemoryAnchorBuilder"}:
        from memory_system.memory_anchor import MemoryAnchor, MemoryAnchorBuilder

        return {"MemoryAnchor": MemoryAnchor, "MemoryAnchorBuilder": MemoryAnchorBuilder}[name]
    if name == "MemoryContextHydrator":
        from memory_system.context_hydrator import MemoryContextHydrator

        return MemoryContextHydrator
    raise AttributeError(name)
