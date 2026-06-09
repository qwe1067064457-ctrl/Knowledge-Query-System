from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from intent.model_runtime.evidence_patch import EvidencePatch
from intent.schema.intent_types import ControlSignal, IntentEvidence, IntentInput, ResolvedIntent


class IntentLLMFallbackAdapter(Protocol):
    def adjudicate(
        self,
        *,
        intent_input: IntentInput,
        history: Iterable[dict[str, object]],
        evidence: IntentEvidence,
        resolved: ResolvedIntent,
        control: ControlSignal,
    ) -> EvidencePatch | None: ...


@dataclass
class LLMIntentFallbackAdapter:
    prompt_path: Path

    def adjudicate(
        self,
        *,
        intent_input: IntentInput,
        history: Iterable[dict[str, object]],
        evidence: IntentEvidence,
        resolved: ResolvedIntent,
        control: ControlSignal,
    ) -> EvidencePatch | None:
        from llm.model_factory import build_intent_fallback_model

        model = build_intent_fallback_model()
        prompt = self.prompt_path.read_text(encoding="utf-8")
        payload = {
            "intent_input": intent_input.to_dict(),
            "history": list(history),
            "evidence": evidence.to_grouped_dict(),
            "resolved": resolved.to_grouped_dict(),
            "control": control.to_grouped_dict(),
        }
        response = model.invoke(
            [
                ("system", prompt),
                ("human", json.dumps(payload, ensure_ascii=False, indent=2)),
            ]
        )
        content = getattr(response, "content", "")
        parsed = _parse_json_payload(str(content))
        if not parsed:
            return None
        return EvidencePatch(
            valid=bool(parsed.get("valid", True)),
            main_intent_probs=_score_dict(parsed.get("main_intent_probs")),
            task_complexity_probs=_score_dict(parsed.get("task_complexity_probs")),
            task_shape_probs=_score_dict(parsed.get("task_shape_probs")),
            task_topology_probs=_score_dict(parsed.get("task_topology_probs")),
            context_dependency_probs=_score_dict(parsed.get("context_dependency_probs")),
            handling_mode_probs=_score_dict(parsed.get("handling_mode_probs")),
            modifier_scores=_score_dict(parsed.get("modifier_scores")),
            context_scores=_score_dict(parsed.get("context_scores")),
            safety_scores=_score_dict(parsed.get("safety_scores")),
            ambiguity_scores=_score_dict(parsed.get("ambiguity_scores")),
            low_confidence=parsed.get("low_confidence"),
            confidence=parsed.get("confidence"),
            reason=str(parsed.get("reason", "llm-fallback")),
        )


def _parse_json_payload(content: str) -> dict[str, object] | None:
    text = content.strip()
    if "```" in text:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _score_dict(value: object) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): float(score) for key, score in value.items()}
