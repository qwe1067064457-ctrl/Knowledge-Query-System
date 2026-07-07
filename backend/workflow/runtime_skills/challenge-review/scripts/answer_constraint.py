"""Deterministic answer-constraint assembly for challenge outputs."""

from __future__ import annotations


def assemble(*, status: str, findings: list[dict] | None = None) -> dict[str, object]:
    return {
        "status": str(status or "").strip(),
        "finding_count": len(findings or []),
        "must_acknowledge_uncertainty": str(status or "") == "insufficient_evidence",
    }
