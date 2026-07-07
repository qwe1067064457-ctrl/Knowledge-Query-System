"""Deterministic query rewrite wrapper used after target resolution."""

from __future__ import annotations


def rewrite(*, query: str, resolved_target: str | None = None) -> dict[str, str]:
    if resolved_target:
        return {"query": f"{resolved_target} {query}".strip()}
    return {"query": str(query or "").strip()}
