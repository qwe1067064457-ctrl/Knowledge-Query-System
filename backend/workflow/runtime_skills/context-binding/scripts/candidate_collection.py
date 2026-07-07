"""Deterministic candidate collection helper for runtime skill wiring."""

from __future__ import annotations


def collect(entries: list[dict], limit: int = 20) -> list[dict]:
    return [dict(item) for item in entries[: max(0, limit)]]
