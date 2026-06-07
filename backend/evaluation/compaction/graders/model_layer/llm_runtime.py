from __future__ import annotations

import json

from llm.model_factory import build_chat_model
from llm.output_sanitizer import sanitize_model_text
from llm.response_utils import stringify_content

from evaluation.compaction.graders.model_layer.compaction_llm_grader import CompactionLLMGrader


class CompactionLLMRuntime:
    def __init__(self) -> None:
        self.grader = CompactionLLMGrader()

    def grade_case(self, case: dict[str, object]) -> dict[str, object]:
        return self.grader.grade(case, invoke=self._invoke_dimension_prompt)

    def _invoke_dimension_prompt(self, dimension: str, prompt: str) -> dict[str, object]:
        model = build_chat_model()
        response = model.invoke([{"role": "user", "content": prompt}])
        text = sanitize_model_text(stringify_content(getattr(response, "content", ""))).strip()
        if not text:
            raise ValueError(f"Empty LLM grader response for {dimension}")
        fenced = None
        if "```" in text:
            parts = text.split("```")
            if len(parts) >= 3:
                fenced = parts[1]
                if fenced.lstrip().startswith("json"):
                    fenced = fenced.lstrip()[4:].strip()
        for candidate in [item for item in (fenced, text) if item]:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        raise ValueError(f"Invalid JSON grader response for {dimension}: {text[:120]}")
