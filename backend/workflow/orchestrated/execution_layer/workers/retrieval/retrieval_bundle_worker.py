from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class RetrievalBundleWorker(BaseWorker):
    name = "retrieval_bundle"
    description = "Project an evidence bundle into registry candidates and summary metadata."

    def run(self, evidence_bundle):
        if evidence_bundle is None:
            return {"evidence_candidates": [], "source_refs": [], "quality_summary": {}}
        return {
            "evidence_candidates": list(evidence_bundle.to_evidence_ref_candidates()),
            "source_refs": list(evidence_bundle.source_ref_list()),
            "quality_summary": dict(evidence_bundle.quality_summary),
        }

