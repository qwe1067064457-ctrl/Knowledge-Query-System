from __future__ import annotations

from workflow.orchestrated.execution_layer.contracts.unit_result import SynthesisResultPayload
from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class CautionAssemblyWorker(BaseWorker):
    name = "caution_assembly"
    description = "Assemble degraded, skipped, blocked, and synthesis cautions into a stable caution list."

    def run(self, unit_results: list[dict] | tuple[dict, ...]):
        cautions: list[str] = []
        for item in unit_results:
            state = str(item.get("state", "pending"))
            unit_id = str(item.get("unit_id", ""))
            if state in {"degraded", "blocked", "skipped"}:
                cautions.append(f"{unit_id}:{state}")
            payload = SynthesisResultPayload.from_dict(dict(item.get("result_payload", {}) or {}))
            for caution in payload.cautions:
                if caution not in cautions:
                    cautions.append(caution)
        return {"cautions": cautions}

