from __future__ import annotations

from dataclasses import replace

from workflow.routes.base import BaseRouteRunner, RouteExecutionRequest
from workflow.types import WorkflowPlan


class RejectRouteRunner(BaseRouteRunner):
    route_name = "reject"

    def run(self, plan: WorkflowPlan, request: RouteExecutionRequest):
        payload = self._build_payload(
            plan,
            request,
            ("Treat this request as rejected and do not enter the normal execution flow.",),
            status="rejected",
        )
        reason_code, reason = self._reject_reason(plan)
        key_events = self._reject_key_events(reason_code)
        answer_constraints = {
            **payload.answer_constraints,
            "allow_substantive_answer": False,
            "must_ask_clarification_first": reason_code == "clarification_first_reject",
            "must_explain_boundary": reason_code in {"policy_reject", "capability_reject"},
            "must_offer_safe_alternative": reason_code in {"policy_reject", "capability_reject"},
        }
        context_bundle = replace(
            payload.context_bundle_obj(),
            reject_summary={
                "reason_code": reason_code,
                "reason": reason,
            },
        )
        status = "needs_clarification" if reason_code == "clarification_first_reject" else "rejected"
        return self._finalize_payload(
            payload,
            plan,
            context_bundle=context_bundle,
            answer_constraints=answer_constraints,
            key_events=key_events,
            status=status,
        )

    def _reject_reason(self, plan: WorkflowPlan) -> tuple[str, str]:
        if plan.handling_mode == "unsupported":
            return "policy_reject", "当前请求命中不支持或应拦截的处理边界"
        if plan.action == "reject":
            return "capability_reject", "当前请求超出本 route 可继续处理的能力边界"
        if plan.should_ask_clarification_first or plan.policy_flags.ask_clarification_first:
            return "clarification_first_reject", "当前缺少关键上下文，需先澄清后再继续"
        if plan.trace.missing_context_types:
            return "missing_context_reject", "当前上下文信息不足，暂不应继续正常处理"
        return "capability_reject", "当前请求超出本 route 可继续处理的能力边界"

    def _reject_key_events(self, reason_code: str) -> tuple[str, ...]:
        if reason_code == "policy_reject":
            return ("policy_reject",)
        if reason_code == "capability_reject":
            return ("capability_reject",)
        if reason_code == "clarification_first_reject":
            return ("clarification_required",)
        return ()
