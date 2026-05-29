from __future__ import annotations

from workflow.orchestrated.execution_layer.contracts.graph import ExecutionUnit


class ExecutionStateMachine:
    """Execution unit state transitions.

    本质作用：
    - 把 execution unit 的运行时命运显式化
    - 让 planner 只负责给图，execution layer 负责推进状态
    """

    _PROCEEDING_STATES = {"completed", "degraded"}

    def can_proceed(self, *, unit: ExecutionUnit, state_by_unit: dict[str, str]) -> bool:
        for dependency in unit.depends_on:
            if state_by_unit.get(dependency) not in self._PROCEEDING_STATES:
                return False
        if unit.proceed_if == "all_dependencies_completed":
            return all(state_by_unit.get(dependency) == "completed" for dependency in unit.depends_on)
        return True
