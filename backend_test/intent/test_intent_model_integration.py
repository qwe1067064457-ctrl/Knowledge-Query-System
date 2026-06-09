from __future__ import annotations

from dataclasses import dataclass

from intent.model_runtime.evidence_patch import EvidencePatch
from intent.pipeline.classifier import classify_intent
from intent.schema.intent_types import CandidateIntent, IntentModifiers, ModelResult, TaskCandidate


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


@dataclass
class StubLLMFallbackAdapter:
    patch: EvidencePatch | None = None
    should_raise: bool = False
    calls: int = 0

    def adjudicate(self, **kwargs):
        self.calls += 1
        if self.should_raise:
            raise RuntimeError("llm fallback failed")
        return self.patch


def test_model_evidence_can_add_soft_doubt_and_task_candidate() -> None:
    adapter = StubIntentModelAdapter(
        result=ModelResult(
            valid=True,
            candidate_intents=(CandidateIntent(intent="chat", score=0.99),),
            modifiers=IntentModifiers(soft_doubt=True),
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
    assert result.control.route == "orchestrated"
    assert result.evidence.model_result is not None
    assert result.evidence.model_result.main_intent_probs == {}
    assert result.evidence.model_result.candidate_intents[0].intent == "chat"


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


def test_challenge_request_uses_rule_plus_model_and_keeps_model_evidence() -> None:
    adapter = StubIntentModelAdapter(
        result=ModelResult(
            valid=True,
            modifier_scores={"challenge": 0.81, "ask_source": 0.74},
            handling_mode_probs={"challenge": 0.88, "clarify": 0.08, "normal": 0.04},
            task_shape_probs={"single_question": 0.72, "compare": 0.28},
            confidence="medium",
            reason="challenge-evidence-from-model",
        )
    )

    result = classify_intent(
        "你刚才这个依据是什么，是不是不对？",
        LAW_HISTORY,
        model_adapter=adapter,
        enable_model_evidence=True,
    )

    assert result.evidence.classifier_mode == "rule_plus_model"
    assert result.evidence.model_result is not None
    assert result.resolved.modifiers.challenge is True
    assert result.resolved.modifiers.ask_source is True
    assert result.control.mode == "challenge"


def test_llm_fallback_can_patch_low_confidence_model_result() -> None:
    adapter = StubIntentModelAdapter(
        result=ModelResult(
            valid=True,
            task_shape_probs={"single_question": 0.52, "compare": 0.48},
            task_topology_probs={"single": 0.55, "staged": 0.45},
            task_complexity_probs={"simple": 0.4, "complex": 0.6},
            handling_mode_probs={"normal": 0.51, "challenge": 0.49},
            low_confidence=True,
            confidence="low",
            reason="low-margin",
        )
    )
    fallback = StubLLMFallbackAdapter(
        patch=EvidencePatch(
            task_complexity_probs={"complex": 0.92},
            task_shape_probs={"compare": 0.88, "single_question": 0.12},
            task_topology_probs={"staged": 0.81, "single": 0.19},
            reason="llm-promoted-compare-staged",
            confidence="high",
            low_confidence=False,
        )
    )

    result = classify_intent(
        "劳动合同法中试用期最长多久？",
        LAW_HISTORY,
        model_adapter=adapter,
        enable_model_evidence=True,
        llm_fallback_adapter=fallback,
        enable_llm_fallback=True,
    )

    assert fallback.calls == 1
    assert result.resolved.task.complexity == "complex"
    assert result.resolved.task.shape == "compare"
    assert result.resolved.task.topology == "staged"
    assert result.control.route == "orchestrated"
    assert result.evidence.model_result is not None
    assert result.evidence.model_result.low_confidence is False
    assert "llm-promoted-compare-staged" in result.evidence.model_result.reason


def test_llm_fallback_skips_high_confidence_regular_case() -> None:
    adapter = StubIntentModelAdapter(
        result=ModelResult(
            valid=True,
            task_shape_probs={"single_question": 0.91},
            task_topology_probs={"single": 0.93},
            task_complexity_probs={"simple": 0.89},
            context_dependency_probs={"none": 0.94},
            handling_mode_probs={"normal": 0.95},
            confidence="high",
            reason="high-confidence-regular",
        )
    )
    fallback = StubLLMFallbackAdapter(
        patch=EvidencePatch(reason="should-not-be-used")
    )

    result = classify_intent(
        "劳动合同法中试用期最长多久？",
        LAW_HISTORY,
        model_adapter=adapter,
        enable_model_evidence=True,
        llm_fallback_adapter=fallback,
        enable_llm_fallback=True,
    )

    assert fallback.calls == 0
    assert result.resolved.task.shape == "single_question"
    assert result.control.route == "qa"


def test_llm_fallback_failure_keeps_small_model_plus_rule_result() -> None:
    adapter = StubIntentModelAdapter(
        result=ModelResult(
            valid=True,
            task_shape_probs={"single_question": 0.52, "mixed": 0.48},
            task_topology_probs={"single": 0.6, "staged": 0.4},
            task_complexity_probs={"simple": 0.45, "complex": 0.55},
            handling_mode_probs={"normal": 0.52, "scope_info": 0.48},
            low_confidence=True,
            confidence="low",
            reason="low-confidence-small-model",
        )
    )
    fallback = StubLLMFallbackAdapter(should_raise=True)

    result = classify_intent(
        "劳动合同法中试用期最长多久？",
        LAW_HISTORY,
        model_adapter=adapter,
        enable_model_evidence=True,
        llm_fallback_adapter=fallback,
        enable_llm_fallback=True,
    )

    assert fallback.calls == 1
    assert result.evidence.model_result is not None
    assert result.evidence.model_result.reason == "low-confidence-small-model"
    assert result.resolved.task.shape == "mixed"
