from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.binding.candidate_collection_worker import CandidateCollectionWorker
from workflow.orchestrated.execution_layer.workers.binding.query_rewrite_worker import QueryRewriteWorker
from workflow.orchestrated.execution_layer.workers.binding.target_resolution_worker import TargetResolutionWorker


def build_context_binding_workers(*, context_binding_power, binding_worker=None):
    workers = [
        CandidateCollectionWorker(context_binding_power),
        TargetResolutionWorker(context_binding_power),
        QueryRewriteWorker(),
    ]
    if binding_worker is not None:
        from workflow.orchestrated.execution_layer.workers.binding.relevant_set_worker import RelevantSetWorker

        workers.insert(1, RelevantSetWorker(binding_worker))
    return tuple(workers)
