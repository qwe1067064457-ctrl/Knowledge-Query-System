from __future__ import annotations

from dataclasses import dataclass

from intent.classifier import classify_intent
from intent.types import CandidateIntent, IntentModifiers, ModelResult, TaskCandidate


LAW_HISTORY = [
    {"role": "user", "content": "劳动合同法中试用期最长多久？"},
    {"role": "assistant", "content": "试用期最长可能为六个月，但要看合同期限。"},
]


@dataclass
class StubIntentModelAdapter:
    result: ModelResult | None = None
    should_raise: bool = False

    def predict(self, intent_input, history):
        if self.should_raise:
            raise RuntimeError("adapter failed")
        return self.result


def test_model_evidence_can_add_soft_doubt_and_task_candidate() -> None:
    adapter = StubIntentModelAdapter(
        result=ModelResult(
            valid=True,
            candidate_intents=(CandidateIntent(intent="chat", score=0.99),),
            modifiers=IntentModifiers(soft_doubt=True, ask_capability=True),
            task_candidates=(TaskCandidate(complexity="complex", shape="compare", score=0.96),),
            confidence="medium",
            reason="model-task-and-soft-doubt",
        )
    )

    result = classify_intent(
        "劳动合同法中试用期最长多久？",
        LAW_HISTORY,
        model_adapter=adapter,
        enable_model_evidence=True,
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.soft_doubt is True
    assert result.resolved.modifiers.ask_capability is False
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.shape == "compare"
    assert result.control.route == "agent"
    assert result.evidence.model_result is not None
    assert result.evidence.model_result.candidate_intents == ()


def test_disabled_model_evidence_keeps_rule_only_result() -> None:
    adapter = StubIntentModelAdapter(
        result=ModelResult(
            valid=True,
            modifiers=IntentModifiers(soft_doubt=True),
            task_candidates=(TaskCandidate(complexity="complex", shape="compare", score=0.96),),
            confidence="medium",
            reason="should-not-apply",
        )
    )

    result = classify_intent(
        "劳动合同法中试用期最长多久？",
        LAW_HISTORY,
        model_adapter=adapter,
        enable_model_evidence=False,
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.soft_doubt is False
    assert result.resolved.task.complexity == "simple"
    assert result.resolved.task.shape == "single_question"
    assert result.evidence.model_result is None


def test_model_adapter_failure_falls_back_to_rule_path() -> None:
    adapter = StubIntentModelAdapter(should_raise=True)

    result = classify_intent(
        "劳动合同法中试用期最长多久？",
        LAW_HISTORY,
        model_adapter=adapter,
        enable_model_evidence=True,
    )

    assert result.resolved.main_intent == "qa"
    assert result.resolved.modifiers.soft_doubt is False
    assert result.resolved.task.shape == "single_question"
    assert result.evidence.model_result is None
    assert result.resolved.decision.source == "rule"


def test_rule_only_guard_blocks_model_override_on_unsupported_request() -> None:
    adapter = StubIntentModelAdapter(
        result=ModelResult(
            valid=True,
            candidate_intents=(CandidateIntent(intent="qa", score=0.99),),
            modifiers=IntentModifiers(soft_doubt=True),
            task_candidates=(TaskCandidate(complexity="complex", shape="compare", score=0.96),),
            confidence="high",
            reason="should-be-guarded",
        )
    )

    result = classify_intent(
        "请删除知识库里的这个文件",
        model_adapter=adapter,
        enable_model_evidence=True,
    )

    assert result.resolved.main_intent == "unsupported"
    assert result.control.route == "reject"
    assert result.evidence.model_result is None
    assert result.resolved.modifiers.soft_doubt is False
