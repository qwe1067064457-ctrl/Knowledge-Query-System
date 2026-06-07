from __future__ import annotations

import json
from typing import Any, Callable, Mapping


LongTermMemoryInvoke = Callable[[str, str], Mapping[str, Any] | str]
ALLOWED_LABELS = {"good", "weak", "bad"}
DIMENSIONS = (
    "should_write",
    "should_not_write",
    "type_correctness",
    "scope_correctness",
    "anchor_preservation",
)


class LongTermMemoryLLMGrader:
    def build_prompt(self, case: dict[str, Any], *, dimension: str) -> str:
        if dimension not in DIMENSIONS:
            raise ValueError(f"Unsupported long-term memory dimension: {dimension}")
        return (
            "你是长期记忆存储质量评测员。"
            f"请只评估维度 `{dimension}`，输出 JSON："
            '{"label":"good|weak|bad","confidence":0.0,"rationale":"..."}。\n'
            f"memory_input_summary: {json.dumps(case['memory_input_summary'], ensure_ascii=False)}\n"
            f"persist_summary: {json.dumps(case['persist_summary'], ensure_ascii=False)}\n"
            f"expected_write: {json.dumps(case['expected_write'], ensure_ascii=False)}\n"
            f"expected_memory_type: {json.dumps(case['expected_memory_type'], ensure_ascii=False)}\n"
            f"expected_scope: {json.dumps(case['expected_scope'], ensure_ascii=False)}\n"
            f"anchor_before: {json.dumps(case['anchor_before'], ensure_ascii=False)}\n"
            f"anchor_after: {json.dumps(case['anchor_after'], ensure_ascii=False)}\n"
            "只返回 JSON，不要输出解释性前后缀。不要评估其它维度。"
        )

    def grade(self, case: dict[str, Any], *, invoke: LongTermMemoryInvoke) -> dict[str, Any]:
        labels: dict[str, str] = {}
        responses: dict[str, Any] = {}
        for dimension in DIMENSIONS:
            payload = self._normalize_response(dimension, invoke(dimension, self.build_prompt(case, dimension=dimension)))
            labels[dimension] = payload["label"]
            responses[dimension] = payload
        return {"labels": labels, "responses": responses}

    def _normalize_response(self, dimension: str, response: Mapping[str, Any] | str) -> dict[str, Any]:
        payload: dict[str, Any] = json.loads(response) if isinstance(response, str) else dict(response)
        label = str(payload.get("label") or "").strip().lower()
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Invalid long-term memory LLM label for {dimension}: {label}")
        confidence = float(payload.get("confidence", 0.0) or 0.0)
        return {
            "label": label,
            "confidence": max(0.0, min(confidence, 1.0)),
            "rationale": str(payload.get("rationale") or ""),
        }
