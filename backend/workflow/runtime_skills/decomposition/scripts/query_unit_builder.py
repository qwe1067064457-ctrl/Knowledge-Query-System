"""Deterministic query-unit assembly for decomposition outputs."""

from __future__ import annotations


def build(units: list[str]) -> list[dict[str, str]]:
    return [
        {
            "unit_id": f"q{index}",
            "text": str(text).strip(),
            "origin": "primary",
        }
        for index, text in enumerate(units, start=1)
        if str(text).strip()
    ]
