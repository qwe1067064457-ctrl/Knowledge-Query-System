from __future__ import annotations

from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.workflow_answer.graders.model_layer.answer_llm_grader import AnswerLLMGrader
from evaluation.workflow_answer.graders.model_layer.retrieval_llm_grader import RetrievalLLMGrader
from evaluation.workflow_answer.graders.rule_layer.answer_rules import grade_answer_case
from evaluation.workflow_answer.graders.rule_layer.retrieval_rules import grade_retrieval_case


def _case(**overrides):
    payload = {
        "case_id": "case_001",
        "trace_id": "trace_001",
        "source": "offline_seed",
        "user_query": "劳动合同试用期最长多久？",
        "knowledge_evidence_summary": {
            "retrieval_quality_status": "good",
            "query_unit_count": 1,
            "merged_evidence_count": 2,
            "source_ref_count": 1,
            "missing_evidence": False,
        },
        "retrieval_summary": {"evidence_summary": {"merged_evidence_count": 2}},
        "workflow_summary": {"evidence_summary": {"merged_evidence_count": 2}},
        "answer_text": "试用期时长与合同期限相关。",
        "core_summary_present": True,
        "user_feedback": None,
    }
    payload.update(overrides)
    return payload


def test_retrieval_rule_grader_scores_and_labels_positive_case() -> None:
    result = grade_retrieval_case(
        _case(),
        semantic_labels={"relevance": "good", "sufficiency": "good", "usability": "good"},
    )

    assert result["dimension_labels"]["presence"] == "good"
    assert result["label"] == "good"
    assert result["score"] == pytest.approx(1.0)


def test_retrieval_rule_grader_applies_presence_hard_cap() -> None:
    case = _case(
        knowledge_evidence_summary={
            "retrieval_quality_status": "good",
            "query_unit_count": 1,
            "merged_evidence_count": 0,
            "source_ref_count": 0,
            "missing_evidence": True,
        }
    )
    result = grade_retrieval_case(
        case,
        semantic_labels={"relevance": "good", "sufficiency": "good", "usability": "good"},
    )

    assert result["dimension_labels"]["presence"] == "bad"
    assert result["label"] == "bad"
    assert "no_evidence" in result["reasons"]


def test_answer_rule_grader_scores_and_labels_positive_case() -> None:
    result = grade_answer_case(
        _case(),
        semantic_labels={
            "answered": "good",
            "grounded": "good",
            "consistency_with_evidence": "good",
            "constraint_coverage": "good",
            "no_hallucination": "good",
        },
    )

    assert result["label"] == "good"
    assert result["score"] == pytest.approx(1.0)


def test_answer_rule_grader_applies_hallucination_cap() -> None:
    result = grade_answer_case(
        _case(),
        semantic_labels={
            "answered": "good",
            "grounded": "good",
            "consistency_with_evidence": "good",
            "constraint_coverage": "good",
            "no_hallucination": "bad",
        },
    )

    assert result["label"] == "weak"
    assert "hallucination" in result["reasons"]


def test_retrieval_llm_grader_calls_each_dimension_and_parses_payload() -> None:
    grader = RetrievalLLMGrader()

    def invoke(dimension: str, prompt: str):
        assert dimension in prompt
        return {"label": "good" if dimension != "usability" else "weak", "confidence": 0.8, "rationale": "ok"}

    result = grader.grade(_case(), invoke=invoke)

    assert result["labels"] == {"relevance": "good", "sufficiency": "good", "usability": "weak"}
    assert result["responses"]["relevance"]["confidence"] == pytest.approx(0.8)


def test_answer_llm_grader_rejects_invalid_label() -> None:
    grader = AnswerLLMGrader()

    def invoke(_: str, __: str):
        return {"label": "maybe", "confidence": 0.4}

    with pytest.raises(ValueError, match="Invalid answer LLM label"):
        grader.grade(_case(), invoke=invoke)
