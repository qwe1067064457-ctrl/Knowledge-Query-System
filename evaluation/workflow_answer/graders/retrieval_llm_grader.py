from __future__ import annotations

import json
from typing import Any, Callable, Mapping


RetrievalInvoke = Callable[[str, str], Mapping[str, Any] | str]
ALLOWED_LABELS = {"good", "weak", "bad"}
DIMENSIONS = ("relevance", "sufficiency", "usability")


class RetrievalLLMGrader:
    def build_prompt(self, case: dict[str, Any], *, dimension: str) -> str:
        if dimension not in DIMENSIONS:
            raise ValueError(f"Unsupported retrieval dimension: {dimension}")
        return (
            "你是 Retrieval 质量评测员。"
            f"请只评估维度 `{dimension}`，输出 JSON："
            '{"label":"good|weak|bad","confidence":0.0,"rationale":"..."}。\n'
            f"user_query: {case['user_query']}\n"
            f"knowledge_evidence_summary: {json.dumps(case['knowledge_evidence_summary'], ensure_ascii=False)}\n"
            f"retrieval_summary: {json.dumps(case['retrieval_summary'], ensure_ascii=False)}\n"
            f"answer_text: {case['answer_text']}\n"
            "不要评估其它维度。"
        )

    def grade(self, case: dict[str, Any], *, invoke: RetrievalInvoke) -> dict[str, Any]:
        labels: dict[str, str] = {}
        responses: dict[str, Any] = {}
        for dimension in DIMENSIONS:
            prompt = self.build_prompt(case, dimension=dimension)
            payload = self._normalize_response(dimension, invoke(dimension, prompt))
            labels[dimension] = payload["label"]
            responses[dimension] = payload
        return {"labels": labels, "responses": responses}

    def _normalize_response(self, dimension: str, response: Mapping[str, Any] | str) -> dict[str, Any]:
        payload: dict[str, Any]
        if isinstance(response, str):
            payload = json.loads(response)
        else:
            payload = dict(response)
        label = str(payload.get("label") or "").strip().lower()
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Invalid retrieval LLM label for {dimension}: {label}")
        confidence = float(payload.get("confidence", 0.0) or 0.0)
        return {
            "label": label,
            "confidence": max(0.0, min(confidence, 1.0)),
            "rationale": str(payload.get("rationale") or ""),
        }
