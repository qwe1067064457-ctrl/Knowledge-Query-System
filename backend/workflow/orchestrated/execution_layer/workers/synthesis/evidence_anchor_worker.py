from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class EvidenceAnchorWorker(BaseWorker):
    name = "evidence_anchor"
    description = "Project evidence anchors from an evidence bundle."

    def run(self, evidence_bundle):
        if evidence_bundle is None:
            return {"evidence_anchors": []}
        return {
            "evidence_anchors": [
                {"source_ref": source_ref, "supports": "workflow_evidence_bundle"}
                for source_ref in evidence_bundle.source_ref_list()[:5]
            ]
        }

