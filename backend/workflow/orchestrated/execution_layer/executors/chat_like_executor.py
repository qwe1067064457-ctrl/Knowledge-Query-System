from workflow.orchestrated.execution_layer.executors.registry import BaseCapabilityExecutor, CapabilityExecutionPlan


class ChatLikeExecutor(BaseCapabilityExecutor):
    capability = "chat_like"

    def plan(self, *, unit, request, working_memory=None) -> CapabilityExecutionPlan:
        del request, working_memory
        return CapabilityExecutionPlan(
            effective_goal=unit.goal,
            allow_retrieval=False,
            notes=("chat_like_executor",),
        )
