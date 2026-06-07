from __future__ import annotations

from workflow.orchestrated.answer_layer.contracts.answer_assembly_package import (
    AnswerAssemblyFinding,
    AnswerAssemblyPackage,
    EvidenceAnchor,
)
from workflow.orchestrated.execution_layer.contracts.unit_result import (
    CompareResultPayload,
    SynthesisResultPayload,
    VerifyResultPayload,
    normalize_result_payload,
)


def build_answer_assembly_package(*, question: str, payload) -> AnswerAssemblyPackage:
    plan_bundle = payload.plan_bundle_obj()
    unit_results = plan_bundle.unit_result_objs()
    completed = tuple(item.unit_id for item in unit_results if item.state == "completed")
    degraded = tuple(item.unit_id for item in unit_results if item.state == "degraded")
    blocked = tuple(item.unit_id for item in unit_results if item.state == "blocked")
    skipped = tuple(item.unit_id for item in unit_results if item.state == "skipped")

    findings: list[AnswerAssemblyFinding] = []
    primary_findings: list[AnswerAssemblyFinding] = []
    supporting_findings: list[AnswerAssemblyFinding] = []
    status_findings: list[AnswerAssemblyFinding] = []
    for item in unit_results:
        role = "support"
        if item.output_slot == "final_answer" or item.capability == "synthesis":
            role = "primary"
        elif item.state in {"blocked", "skipped", "degraded"}:
            role = item.state
        summary = _result_payload_summary(item)
        if item.skipped_reason:
            summary = f"{summary}, reason={item.skipped_reason}"
        finding = AnswerAssemblyFinding(
            unit_id=item.unit_id,
            role=role,
            summary=summary,
            confidence=_result_payload_confidence(item),
        )
        findings.append(finding)
        if role == "primary":
            primary_findings.append(finding)
        elif role == "support":
            supporting_findings.append(finding)
        else:
            status_findings.append(finding)

    evidence_bundle = payload.evidence_bundle
    evidence_anchors: list[EvidenceAnchor] = []
    if evidence_bundle is not None:
        for source_ref in evidence_bundle.source_ref_list()[:5]:
            evidence_anchors.append(EvidenceAnchor(source_ref=source_ref, supports="workflow_evidence_bundle"))

    cautions: list[str] = []
    if degraded:
        cautions.append(f"存在 degraded units: {', '.join(degraded)}")
    if blocked:
        cautions.append(f"存在 blocked units: {', '.join(blocked)}")
    if skipped:
        cautions.append(f"存在 skipped units: {', '.join(skipped)}")
    for item in unit_results:
        for caution in _result_payload_cautions(item):
            if caution not in cautions:
                cautions.append(caution)

    return AnswerAssemblyPackage(
        question=question,
        execution_summary={
            "planning_mode": plan_bundle.planning_mode or "not_applicable",
            "completed": list(completed),
            "degraded": list(degraded),
            "blocked": list(blocked),
            "skipped": list(skipped),
        },
        main_findings=tuple(findings),
        primary_findings=tuple(primary_findings),
        supporting_findings=tuple(supporting_findings),
        status_findings=tuple(status_findings),
        evidence_anchors=tuple(evidence_anchors),
        answer_cautions=tuple(cautions),
        route_constraints=dict(payload.answer_constraints),
    )


def _result_payload_summary(item) -> str:
    if item.capability == "verify":
        result_payload = VerifyResultPayload.from_dict(
            normalize_result_payload(capability=item.capability, payload=getattr(item, "result_payload", {}))
        )
        summary = result_payload.summary.strip()
        judgment = result_payload.judgment.strip()
        if summary:
            return summary if not judgment else f"{summary} [judgment={judgment}]"
    elif item.capability == "compare":
        result_payload = CompareResultPayload.from_dict(
            normalize_result_payload(capability=item.capability, payload=getattr(item, "result_payload", {}))
        )
        summary = result_payload.summary.strip()
        if summary:
            if result_payload.tradeoff:
                return f"{summary} [tradeoff={'; '.join(result_payload.tradeoff)}]"
            return summary
    elif item.capability == "synthesis":
        result_payload = SynthesisResultPayload.from_dict(
            normalize_result_payload(capability=item.capability, payload=getattr(item, "result_payload", {}))
        )
        conclusion = result_payload.main_conclusion.strip()
        if conclusion:
            return conclusion
        draft = result_payload.final_text_draft.strip()
        if draft:
            return draft
    return f"{item.unit_id}: capability={item.capability}, state={item.state}, output_slot={item.output_slot or 'not_set'}"


def _result_payload_confidence(item) -> str | None:
    if item.state in {"blocked", "degraded"}:
        return "low"
    if item.capability == "verify":
        return VerifyResultPayload.from_dict(
            normalize_result_payload(capability=item.capability, payload=getattr(item, "result_payload", {}))
        ).confidence
    if item.capability == "compare":
        return CompareResultPayload.from_dict(
            normalize_result_payload(capability=item.capability, payload=getattr(item, "result_payload", {}))
        ).confidence
    if item.capability == "synthesis":
        return SynthesisResultPayload.from_dict(
            normalize_result_payload(capability=item.capability, payload=getattr(item, "result_payload", {}))
        ).confidence
    return None


def _result_payload_cautions(item) -> tuple[str, ...]:
    if item.capability != "synthesis":
        return ()
    payload = SynthesisResultPayload.from_dict(
        normalize_result_payload(capability=item.capability, payload=getattr(item, "result_payload", {}))
    )
    return payload.cautions
