from __future__ import annotations

from workflow.orchestrated.execution_layer.workers.base import BaseWorker


class QueryRewriteWorker(BaseWorker):
    name = "query_rewrite"
    description = "Rewrite a unit query based on an existing binding result."

    def run(self, query: str, binding_result: dict | None = None):
        binding_result = dict(binding_result or {})
        rewritten = str(binding_result.get("rewritten_query") or "").strip()
        fallback_type = str(binding_result.get("fallback_type") or "").strip()
        if rewritten and fallback_type != "retrieve_on_raw_query":
            return {"query": rewritten, "used_binding_rewrite": True}
        return {"query": query, "used_binding_rewrite": False}

