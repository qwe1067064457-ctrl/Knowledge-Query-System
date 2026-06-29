from __future__ import annotations

from dataclasses import dataclass

from intent import classify_intent
from intent.schema.intent_types import CandidateIntent, IntentModifiers, ModelResult


@dataclass
class WeakConflictingModel:
    def predict(self, intent_input, history):
        return ModelResult(
            valid=True,
            candidate_intents=(CandidateIntent(intent="qa", score=0.61),),
            modifiers=IntentModifiers(),
            confidence="medium",
            reason="weak-conflict",
        )


def test_explicit_qa_request_still_routes_to_qa() -> None:
    result = classify_intent("劳动合同法中试用期最长多久？")

    assert result.resolved.main_intent == "qa"
    assert result.control.route == "qa"
    assert result.evidence.typed_evidence
    assert result.evidence.quality_report is not None


def test_weak_model_route_signal_requires_adjudication_but_does_not_force_resolver() -> None:
    result = classify_intent(
        "随便聊两句",
        model_adapter=WeakConflictingModel(),
        enable_model_evidence=True,
    )

    assert result.evidence.quality_report is not None
    assert result.evidence.quality_report.case_level == "requires_adjudication"
    assert result.evidence.adjudication_result is None
    assert result.resolved.main_intent == "chat"
