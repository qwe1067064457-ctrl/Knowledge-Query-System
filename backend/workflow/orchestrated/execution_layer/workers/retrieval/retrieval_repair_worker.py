from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class RetrievalRepairWorker(BaseWorker):
    name = "retrieval_repair"
    description = "Summarize retrieval repair information from an evidence bundle."

    def run(self, evidence_bundle):
        if evidence_bundle is None:
            return {"repairable_units": 0, "repaired_units": 0}
        return {
            "repairable_units": int(evidence_bundle.quality_summary.get("repairable_units", 0) or 0),
            "repaired_units": int(evidence_bundle.quality_summary.get("repaired_units", 0) or 0),
        }

