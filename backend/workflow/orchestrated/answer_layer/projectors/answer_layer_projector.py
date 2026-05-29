from __future__ import annotations

from workflow.orchestrated.answer_layer.contracts.answer_assembly_package import (
    AnswerAssemblyFinding,
    AnswerAssemblyPackage,
    EvidenceAnchor,
)


def build_answer_assembly_package(*, question: str, payload) -> AnswerAssemblyPackage:
    plan_bundle = payload.plan_bundle_obj()
    unit_results = plan_bundle.unit_result_objs()
    completed = tuple(item.unit_id for item in unit_results if item.state == "completed")
    degraded = tuple(item.unit_id for item in unit_results if item.state == "degraded")
    blocked = tuple(item.unit_id for item in unit_results if item.state == "blocked")
    skipped = tuple(item.unit_id for item in unit_results if item.state == "skipped")

    findings: list[AnswerAssemblyFinding] = []
    for item in unit_results:
        role = "support"
        if item.output_slot == "final_answer" or item.capability == "synthesis":
            role = "primary"
        elif item.state in {"blocked", "skipped", "degraded"}:
            role = item.state
        summary = f"{item.unit_id}: capability={item.capability}, state={item.state}, output_slot={item.output_slot or 'not_set'}"
        if item.skipped_reason:
            summary = f"{summary}, reason={item.skipped_reason}"
        findings.append(
            AnswerAssemblyFinding(
                unit_id=item.unit_id,
                role=role,
                summary=summary,
                confidence="low" if item.state in {"blocked", "degraded"} else None,
            )
        )

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
        evidence_anchors=tuple(evidence_anchors),
        answer_cautions=tuple(cautions),
        route_constraints=dict(payload.answer_constraints),
    )
