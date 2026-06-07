from __future__ import annotations

import json
from collections import Counter
from typing import Any, Iterable

from evaluation.core.report_writer import StandardReportWriter
from evaluation.core.runner import TopicRunnerConfig

from evaluation.workflow_answer.finalize_impl import WorkflowAnswerFinalizer
from evaluation.workflow_answer.model_impl import WorkflowAnswerModelEvaluator
from evaluation.workflow_answer.rule_impl import WorkflowAnswerRuleEvaluator


def build_topic_config(
    *,
    use_llm: bool = False,
    retrieval_label_overrides: dict[str, dict[str, str]] | None = None,
    answer_label_overrides: dict[str, dict[str, str]] | None = None,
    retrieval_llm_metadata: dict[str, dict[str, Any]] | None = None,
    answer_llm_metadata: dict[str, dict[str, Any]] | None = None,
) -> TopicRunnerConfig:
    return TopicRunnerConfig(
        topic="workflow_answer",
        rule_evaluator=WorkflowAnswerRuleEvaluator(),
        model_evaluator=WorkflowAnswerModelEvaluator(
            use_llm=use_llm,
            retrieval_label_overrides=retrieval_label_overrides,
            answer_label_overrides=answer_label_overrides,
            retrieval_llm_metadata=retrieval_llm_metadata,
            answer_llm_metadata=answer_llm_metadata,
        ),
        finalizer=WorkflowAnswerFinalizer(),
        report_writer=StandardReportWriter(
            summary_builder=summarize_results,
            markdown_builder=_build_markdown_report,
        ),
    )


def summarize_results(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(results)
    if not rows:
        return {
            "samples": 0,
            "needs_human_review": 0,
            "retrieval": {"labels": {}, "dimension_labels": {}, "reasons": {}, "average_score": 0.0},
            "answer": {"labels": {}, "dimension_labels": {}, "reasons": {}, "average_score": 0.0},
            "source_distribution": {},
            "user_feedback_distribution": {},
        }

    retrieval_labels = Counter()
    answer_labels = Counter()
    source_distribution = Counter()
    feedback_distribution = Counter()
    retrieval_reason_counts = Counter()
    answer_reason_counts = Counter()
    retrieval_dimension_counts: dict[str, Counter[str]] = {}
    answer_dimension_counts: dict[str, Counter[str]] = {}
    needs_human_review = 0
    retrieval_scores = 0.0
    answer_scores = 0.0

    for row in rows:
        retrieval = row["retrieval"]
        answer = row["answer"]
        retrieval_labels.update([retrieval["label"]])
        answer_labels.update([answer["label"]])
        source_distribution.update([row["source"]])
        feedback_distribution.update([str(row.get("user_feedback"))])
        retrieval_reason_counts.update(retrieval.get("reasons", []))
        answer_reason_counts.update(answer.get("reasons", []))
        retrieval_scores += float(retrieval.get("score", 0.0) or 0.0)
        answer_scores += float(answer.get("score", 0.0) or 0.0)
        if row.get("needs_human_review"):
            needs_human_review += 1

        for key, label in retrieval.get("dimension_labels", {}).items():
            retrieval_dimension_counts.setdefault(key, Counter()).update([label])
        for key, label in answer.get("dimension_labels", {}).items():
            answer_dimension_counts.setdefault(key, Counter()).update([label])

    sample_count = len(rows)
    return {
        "samples": sample_count,
        "needs_human_review": needs_human_review,
        "retrieval": {
            "labels": dict(retrieval_labels),
            "dimension_labels": {key: dict(counter) for key, counter in sorted(retrieval_dimension_counts.items())},
            "reasons": dict(retrieval_reason_counts),
            "average_score": round(retrieval_scores / sample_count, 4),
        },
        "answer": {
            "labels": dict(answer_labels),
            "dimension_labels": {key: dict(counter) for key, counter in sorted(answer_dimension_counts.items())},
            "reasons": dict(answer_reason_counts),
            "average_score": round(answer_scores / sample_count, 4),
        },
        "source_distribution": dict(source_distribution),
        "user_feedback_distribution": dict(feedback_distribution),
    }


def _build_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Workflow + Answer Evaluation Report",
        "",
        f"- samples: {summary['samples']}",
        f"- needs_human_review: {summary['needs_human_review']}",
        "",
        "## Retrieval",
        f"- average_score: {summary['retrieval']['average_score']}",
        f"- labels: {json.dumps(summary['retrieval']['labels'], ensure_ascii=False)}",
        f"- reasons: {json.dumps(summary['retrieval']['reasons'], ensure_ascii=False)}",
        "",
        "## Answer",
        f"- average_score: {summary['answer']['average_score']}",
        f"- labels: {json.dumps(summary['answer']['labels'], ensure_ascii=False)}",
        f"- reasons: {json.dumps(summary['answer']['reasons'], ensure_ascii=False)}",
        "",
        "## Traffic",
        f"- source_distribution: {json.dumps(summary['source_distribution'], ensure_ascii=False)}",
        f"- user_feedback_distribution: {json.dumps(summary['user_feedback_distribution'], ensure_ascii=False)}",
        "",
    ]
    return "\n".join(lines)
