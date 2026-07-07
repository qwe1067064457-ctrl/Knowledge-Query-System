from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionGroupState:
    current_group_index: int = 0
    group_retry_count: int = 0
    degraded_units: tuple[str, ...] = ()
    parallel_results: tuple[Any, ...] = field(default_factory=tuple)
