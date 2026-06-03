from __future__ import annotations

from typing import Literal

EVENT_WORKFLOW_RUN = "workflow_run"
EVENT_ANSWER_MODEL_RUN = "answer_model_run"
EVENT_RETRIEVAL_RUN = "retrieval_run"
EVENT_CONTEXT_ASSEMBLY_RUN = "context_assembly_run"
EVENT_COMPACTION_RUN = "compaction_run"
EVENT_PRE_COMPACTION_EXTRACTION_RUN = "pre_compaction_extraction_run"

EventType = Literal[
    "workflow_run",
    "answer_model_run",
    "retrieval_run",
    "context_assembly_run",
    "compaction_run",
    "pre_compaction_extraction_run",
]

RUN_NAME_BY_EVENT_TYPE: dict[EventType, str] = {
    EVENT_WORKFLOW_RUN: "workflow.run",
    EVENT_ANSWER_MODEL_RUN: "answer.run",
    EVENT_RETRIEVAL_RUN: "retrieval.run",
    EVENT_CONTEXT_ASSEMBLY_RUN: "context.assembly",
    EVENT_COMPACTION_RUN: "context.compaction",
    EVENT_PRE_COMPACTION_EXTRACTION_RUN: "memory.pre_compaction_extraction",
}
