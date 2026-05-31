from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from workflow.contracts.graph import ExecutionUnit, GlobalBindingFrame, UnitState
from workflow.runners.base import RouteExecutionRequest
from workflow.types import ContextBindingResult, EvidenceBundle


@dataclass(frozen=True)
class UnitExecutionContext:
    unit: ExecutionUnit
    request: RouteExecutionRequest
    binding_candidates: list[dict[str, Any]]
    global_binding_frame: GlobalBindingFrame
    binding_enabled: bool = False
    allow_retrieval: bool = False
    base_dir: Path | None = None
    recent_power: str | None = None
    recent_object_type: str | None = None


@dataclass(frozen=True)
class UnitExecutionOutcome:
    unit_state: UnitState = "completed"
    result_payload: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    key_events: tuple[str, ...] = ()
    binding_result: ContextBindingResult | None = None
    evidence_bundle: EvidenceBundle | None = None
    evidence_candidates: tuple[dict[str, Any], ...] = ()
    skipped_reason: str | None = None
