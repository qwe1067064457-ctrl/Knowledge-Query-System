from __future__ import annotations

from dataclasses import dataclass

from intent import classify_intent
from intent.schema.evidence_types import AdjudicationResult, TypedEvidence
from intent.schema.intent_types import CandidateIntent, IntentModifiers, ModelResult


@dataclass
class WeakRouteModel:
    def predict(self, intent_input, history):
        return ModelResult(
            valid=True,
            candidate_intents=(CandidateIntent(intent="qa", score=0.61),),
            modifiers=IntentModifiers(),
            confidence="medium",
            reason="weak-route",
        )


@dataclass
class FakeAdjudicator:
    calls: int = 0

    def adjudicate(self, *, intent_input, typed_evidence, quality_report, history):
        self.calls += 1
        corrected = TypedEvidence(
            signal="main_intent",
            value="chat",
            source="llm_adjudication",
            score=0.96,
            threshold=0.6,
            margin=0.36,
            calibration_quality="good",
            prerequisites=(),
            missing_prerequisites=(),
            criticality="route",
            rationale="fake adjudication",
        )
        return AdjudicationResult(
            accepted_evidence=(),
            corrected_evidence=(corrected,),
            rejected_evidence=(),
            clarified_ambiguity_type="route",
            fallback_recommendation="auto_resolve",
            reason="choose chat",
        )


def test_requires_adjudication_calls_adjudicator_and_resolves_with_result() -> None:
    adjudicator = FakeAdjudicator()

    result = classify_intent(
        "随便聊两句",
        model_adapter=WeakRouteModel(),
        adjudicator=adjudicator,
        enable_model_evidence=True,
    )

    assert adjudicator.calls == 1
    assert result.evidence.quality_report is not None
    assert result.evidence.quality_report.case_level == "auto_resolve_with_warnings"
    assert result.evidence.adjudication_result is not None
    assert result.resolved.main_intent == "chat"


def test_non_llm_gate_decisions_do_not_call_adjudicator() -> None:
    adjudicator = FakeAdjudicator()

    classify_intent("你好", adjudicator=adjudicator)
    classify_intent("你确定吗？", adjudicator=adjudicator)
    classify_intent("请删除知识库里的这个文件", adjudicator=adjudicator)

    assert adjudicator.calls == 0


def test_llm_rejected_evidence_does_not_drive_resolver() -> None:
    @dataclass
    class RejectingAdjudicator:
        calls: int = 0

        def adjudicate(self, *, intent_input, typed_evidence, quality_report, history):
            self.calls += 1
            rejected = next(item for item in typed_evidence if item.signal == "main_intent" and item.value == "qa")
            corrected = TypedEvidence(
                signal="main_intent",
                value="chat",
                source="llm_adjudication",
                score=0.96,
                threshold=0.6,
                margin=0.36,
                calibration_quality="good",
                prerequisites=(),
                missing_prerequisites=(),
                criticality="route",
                rationale="fake adjudication",
            )
            return AdjudicationResult(
                accepted_evidence=(),
                corrected_evidence=(corrected,),
                rejected_evidence=(rejected,),
                clarified_ambiguity_type="route",
                fallback_recommendation="auto_resolve",
                reason="reject qa route",
            )

    adjudicator = RejectingAdjudicator()

    result = classify_intent(
        "随便聊两句",
        model_adapter=WeakRouteModel(),
        adjudicator=adjudicator,
        enable_model_evidence=True,
    )

    assert adjudicator.calls == 1
    assert result.resolved.main_intent == "chat"
    assert all(
        not (item.signal == "main_intent" and item.value == "qa" and item.source == "small_model")
        for item in result.evidence.quality_report.accepted_evidence
    )
