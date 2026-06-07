from __future__ import annotations

import json
from typing import Any, Callable, Mapping


AnswerInvoke = Callable[[str, str], Mapping[str, Any] | str]
ALLOWED_LABELS = {"good", "weak", "bad"}
DIMENSIONS = (
    "answered",
    "grounded",
    "consistency_with_evidence",
    "constraint_coverage",
    "no_hallucination",
)


class AnswerLLMGrader:
    def build_prompt(self, case: dict[str, Any], *, dimension: str) -> str:
        if dimension not in DIMENSIONS:
            raise ValueError(f"Unsupported answer dimension: {dimension}")
        dimension_definition = {
            "answered": "是否正面回答了用户当前问题，而不是回避、跑题或只给空泛建议。",
            "grounded": "回答是否立在可见证据与上下文上，而不是脱离依据自行发挥。",
            "consistency_with_evidence": "回答是否与现有证据一致，而不是相互矛盾。",
            "constraint_coverage": "用户明确提出的关键条件、限制或要求是否被覆盖。",
            "no_hallucination": "回答是否出现证据中没有支持、且看起来像编造的内容。",
        }[dimension]
        return (
            "你是 Answer 质量评测员。"
            f"请只评估维度 `{dimension}`，输出 JSON："
            '{"label":"good|weak|bad","confidence":0.0,"rationale":"..."}。\n'
            f"维度定义: {dimension_definition}\n"
            f"user_query: {case['user_query']}\n"
            f"knowledge_evidence_summary: {json.dumps(case['knowledge_evidence_summary'], ensure_ascii=False)}\n"
            f"workflow_summary: {json.dumps(case['workflow_summary'], ensure_ascii=False)}\n"
            f"core_summary_present: {json.dumps(case['core_summary_present'], ensure_ascii=False)}\n"
            f"answer_text: {case['answer_text']}\n"
            "只返回 JSON，不要输出解释性前后缀。不要评估其它维度。"
        )

    def grade(self, case: dict[str, Any], *, invoke: AnswerInvoke) -> dict[str, Any]:
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
            raise ValueError(f"Invalid answer LLM label for {dimension}: {label}")
        confidence = float(payload.get("confidence", 0.0) or 0.0)
        return {
            "label": label,
            "confidence": max(0.0, min(confidence, 1.0)),
            "rationale": str(payload.get("rationale") or ""),
        }
