from __future__ import annotations

from workflow.contracts.graph import ExecutionUnit


def should_execute_unit(*, unit: ExecutionUnit, state_by_unit: dict[str, str]) -> bool:
    if not unit.depends_on:
        return True
    for dependency in unit.depends_on:
        if state_by_unit.get(dependency) != "completed":
            return False
    return True

