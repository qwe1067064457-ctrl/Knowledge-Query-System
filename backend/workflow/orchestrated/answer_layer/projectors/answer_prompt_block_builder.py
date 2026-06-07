from __future__ import annotations

from workflow.orchestrated.answer_layer.contracts.answer_assembly_package import AnswerAssemblyPackage
from workflow.orchestrated.answer_layer.contracts.answer_prompt_blocks import AnswerPromptBlockSet


def build_answer_prompt_blocks(package: AnswerAssemblyPackage) -> AnswerPromptBlockSet:
    question_block = f"[Question]\n{package.question}"
    execution_summary = package.execution_summary
    execution_summary_block = (
        "[Execution Summary]\n"
        f"- planning_mode: {execution_summary.get('planning_mode', 'not_applicable')}\n"
        f"- completed: {', '.join(execution_summary.get('completed', [])) or 'none'}\n"
        f"- degraded: {', '.join(execution_summary.get('degraded', [])) or 'none'}\n"
        f"- blocked: {', '.join(execution_summary.get('blocked', [])) or 'none'}\n"
        f"- skipped: {', '.join(execution_summary.get('skipped', [])) or 'none'}"
    )
    main_findings_lines = ["[Main Findings]"]
    for item in package.main_findings:
        prefix = f"- ({item.role}) {item.summary}"
        if item.confidence:
            prefix += f" [confidence={item.confidence}]"
        main_findings_lines.append(prefix)
    primary_lines = ["[Primary Findings]"]
    if package.primary_findings:
        for item in package.primary_findings:
            prefix = f"- {item.summary}"
            if item.confidence:
                prefix += f" [confidence={item.confidence}]"
            primary_lines.append(prefix)
    else:
        primary_lines.append("- none")
    support_lines = ["[Supporting Findings]"]
    if package.supporting_findings:
        for item in package.supporting_findings:
            prefix = f"- {item.summary}"
            if item.confidence:
                prefix += f" [confidence={item.confidence}]"
            support_lines.append(prefix)
    else:
        support_lines.append("- none")
    status_lines = ["[Status Findings]"]
    if package.status_findings:
        for item in package.status_findings:
            prefix = f"- ({item.role}) {item.summary}"
            if item.confidence:
                prefix += f" [confidence={item.confidence}]"
            status_lines.append(prefix)
    else:
        status_lines.append("- none")
    evidence_lines = ["[Evidence Anchors]"]
    if package.evidence_anchors:
        for item in package.evidence_anchors:
            evidence_lines.append(f"- {item.source_ref} supports {item.supports}")
    else:
        evidence_lines.append("- none")
    caution_lines = ["[Answer Cautions]"]
    if package.answer_cautions:
        caution_lines.extend(f"- {item}" for item in package.answer_cautions)
    else:
        caution_lines.append("- none")
    constraint_lines = ["[Answer Constraints]"]
    if package.route_constraints:
        constraint_lines.extend(f"- {key}: {value}" for key, value in package.route_constraints.items())
    else:
        constraint_lines.append("- none")
    return AnswerPromptBlockSet(
        question_block=question_block,
        execution_summary_block=execution_summary_block,
        main_findings_block="\n".join(main_findings_lines),
        evidence_anchors_block="\n".join(evidence_lines),
        cautions_block="\n".join(caution_lines),
        constraints_block="\n".join(constraint_lines),
        extra_blocks=(
            "\n".join(primary_lines),
            "\n".join(support_lines),
            "\n".join(status_lines),
        ),
    )
