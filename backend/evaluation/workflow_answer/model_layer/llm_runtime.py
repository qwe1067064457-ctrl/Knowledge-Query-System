from __future__ import annotations

import json
from typing import Any

from llm.model_factory import build_chat_model
from llm.output_sanitizer import sanitize_model_text
from llm.response_utils import stringify_content

from evaluation.workflow_answer.model_layer.answer_llm_grader import AnswerLLMGrader
from evaluation.workflow_answer.model_layer.retrieval_llm_grader import RetrievalLLMGrader


class WorkflowAnswerLLMRuntime:
    def __init__(self) -> None:
        self.retrieval_grader = RetrievalLLMGrader()
        self.answer_grader = AnswerLLMGrader()

    def grade_case(self, case: dict[str, Any]) -> dict[str, Any]:
        retrieval = self.retrieval_grader.grade(case, invoke=self._invoke_dimension_prompt)
        answer = self.answer_grader.grade(case, invoke=self._invoke_dimension_prompt)
        return {
            "retrieval": retrieval,
            "answer": answer,
        }

    def _invoke_dimension_prompt(self, dimension: str, prompt: str) -> dict[str, Any]:
        model = build_chat_model()
        response = model.invoke([{"role": "user", "content": prompt}])
        text = sanitize_model_text(stringify_content(getattr(response, "content", ""))).strip()
        return self._extract_json_payload(text, dimension=dimension)

    def _extract_json_payload(self, text: str, *, dimension: str) -> dict[str, Any]:
        if not text:
            raise ValueError(f"Empty LLM grader response for {dimension}")
        fenced = None
        if "```" in text:
            parts = text.split("```")
            if len(parts) >= 3:
                fenced = parts[1]
                if fenced.lstrip().startswith("json"):
                    fenced = fenced.lstrip()[4:].strip()
        candidates = [candidate for candidate in (fenced, text) if candidate]
        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        raise ValueError(f"Invalid JSON grader response for {dimension}: {text[:120]}")
