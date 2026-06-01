from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workflow.contracts import ExecutionGraph
from workflow.types import ContextBindingResult, EvidenceBundle, UnitResult


@dataclass(frozen=True)
class ExecutionLayerResult:
    execution_graph: ExecutionGraph
    unit_results: tuple[UnitResult, ...]
    evidence_bundle: EvidenceBundle | None
    preferred_binding_result: ContextBindingResult | None = None
    evidence_candidates: tuple[dict[str, Any], ...] = ()
    key_events: tuple[str, ...] = ()


ExecutionRuntimeResult = ExecutionLayerResult
ExecutionRunResult = ExecutionLayerResult
