from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.retrieval.retrieval_bundle_worker import RetrievalBundleWorker
from workflow.orchestrated.execution_layer.workers.retrieval.retrieval_execute_worker import RetrievalExecuteWorker
from workflow.orchestrated.execution_layer.workers.retrieval.retrieval_quality_worker import RetrievalQualityWorker
from workflow.orchestrated.execution_layer.workers.retrieval.retrieval_query_builder_worker import RetrievalQueryBuilderWorker
from workflow.orchestrated.execution_layer.workers.retrieval.retrieval_repair_worker import RetrievalRepairWorker


def build_retrieval_workers(*, retrieval_power, review_worker):
    return (
        RetrievalQueryBuilderWorker(),
        RetrievalExecuteWorker(retrieval_power),
        RetrievalRepairWorker(),
        RetrievalBundleWorker(),
        RetrievalQualityWorker(review_worker),
    )

