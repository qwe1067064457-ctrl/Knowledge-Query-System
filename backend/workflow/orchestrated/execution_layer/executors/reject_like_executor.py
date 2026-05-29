from workflow.orchestrated.execution_layer.executors.registry import BaseCapabilityExecutor, CapabilityExecutionPlan


class RejectLikeExecutor(BaseCapabilityExecutor):
    capability = "reject_like"

    def plan(self, *, unit, request, working_memory=None) -> CapabilityExecutionPlan:
        del request, working_memory
        return CapabilityExecutionPlan(
            effective_goal=unit.goal,
            allow_retrieval=False,
            terminal_state="completed",
            terminal_reason="reject_like_executor",
            notes=("reject_like_executor",),
        )
