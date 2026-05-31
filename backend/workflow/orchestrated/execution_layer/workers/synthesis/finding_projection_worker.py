from __future__ import annotations

from workflow.orchestrated.answer_layer.projectors.answer_layer_projector import build_answer_assembly_package
from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class FindingProjectionWorker(BaseWorker):
    name = "finding_projection"
    description = "Project execution payload into primary, supporting, and status findings."

    def run(self, question: str, payload):
        package = build_answer_assembly_package(question=question, payload=payload)
        return {
            "primary_findings": [item.to_dict() for item in package.primary_findings],
            "supporting_findings": [item.to_dict() for item in package.supporting_findings],
            "status_findings": [item.to_dict() for item in package.status_findings],
        }

