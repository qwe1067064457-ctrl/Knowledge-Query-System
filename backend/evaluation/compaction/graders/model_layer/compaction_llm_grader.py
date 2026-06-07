from __future__ import annotations

import json
from typing import Any, Callable, Mapping


CompactionInvoke = Callable[[str, str], Mapping[str, Any] | str]
ALLOWED_LABELS = {"good", "weak", "bad"}
DIMENSIONS = (
    "key_info_preserved",
    "anchor_recoverability",
    "post_compaction_sufficiency",
    "pre_compaction_extraction_coverage",
)


class CompactionLLMGrader:
    def build_prompt(self, case: dict[str, Any], *, dimension: str) -> str:
        if dimension not in DIMENSIONS:
            raise ValueError(f"Unsupported compaction dimension: {dimension}")
        return (
            "你是上下文压缩保真质量评测员。"
            f"请只评估维度 `{dimension}`，输出 JSON："
            '{"label":"good|weak|bad","confidence":0.0,"rationale":"..."}。\n'
            f"pre_compaction_summary: {json.dumps(case['pre_compaction_summary'], ensure_ascii=False)}\n"
            f"post_compaction_summary: {json.dumps(case['post_compaction_summary'], ensure_ascii=False)}\n"
            f"pre_compaction_extraction_summary: {json.dumps(case['pre_compaction_extraction_summary'], ensure_ascii=False)}\n"
            f"expected_anchor_required: {json.dumps(case['expected_anchor_required'], ensure_ascii=False)}\n"
            "只返回 JSON，不要输出解释性前后缀。不要评估其它维度。"
        )

    def grade(self, case: dict[str, Any], *, invoke: CompactionInvoke) -> dict[str, Any]:
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
            raise ValueError(f"Invalid compaction LLM label for {dimension}: {label}")
        confidence = float(payload.get("confidence", 0.0) or 0.0)
        return {
            "label": label,
            "confidence": max(0.0, min(confidence, 1.0)),
            "rationale": str(payload.get("rationale") or ""),
        }
