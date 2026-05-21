from __future__ import annotations

from typing import Any


class BindingWorker:
    def bind(self, *, query: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            return {"binding_ambiguous": True, "bound_targets": ()}
        return {
            "binding_ambiguous": False,
            "bound_targets": (candidates[-1],),
            "binding_confidence": "medium",
            "notes": ("worker_binding",),
        }
