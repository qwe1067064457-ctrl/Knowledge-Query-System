from __future__ import annotations

import json
from collections import Counter
from typing import Any, Iterable

from evaluation.core.report_writer import StandardReportWriter
from evaluation.core.runner import TopicRunnerConfig
from evaluation.working_memory.graders.finalize_layer.finalizer import WorkingMemoryFinalizer
from evaluation.working_memory.graders.model_layer.model_evaluator import WorkingMemoryModelEvaluator
from evaluation.working_memory.graders.rule_layer.rule_evaluator import WorkingMemoryRuleEvaluator


def build_topic_config(
    *,
    use_llm: bool = False,
    label_overrides: dict[str, dict[str, str]] | None = None,
    llm_metadata_overrides: dict[str, dict[str, Any]] | None = None,
) -> TopicRunnerConfig:
    return TopicRunnerConfig(
        topic="working_memory",
        rule_evaluator=WorkingMemoryRuleEvaluator(),
        model_evaluator=WorkingMemoryModelEvaluator(
            use_llm=use_llm,
            label_overrides=label_overrides,
            llm_metadata_overrides=llm_metadata_overrides,
        ),
        finalizer=WorkingMemoryFinalizer(),
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
            "labels": {},
            "dimension_labels": {},
            "reasons": {},
            "average_score": 0.0,
            "source_distribution": {},
            "user_feedback_distribution": {},
        }

    labels = Counter()
    source_distribution = Counter()
    feedback_distribution = Counter()
    reason_counts = Counter()
    dimension_counts: dict[str, Counter[str]] = {}
    score_sum = 0.0
    needs_human_review = 0
    for row in rows:
        labels.update([row["label"]])
        source_distribution.update([row["source"]])
        feedback_distribution.update([str(row.get("user_feedback"))])
        reason_counts.update(row.get("reasons", []))
        score_sum += float(row.get("score", 0.0) or 0.0)
        if row.get("needs_human_review"):
            needs_human_review += 1
        for key, label in row.get("dimension_labels", {}).items():
            dimension_counts.setdefault(key, Counter()).update([label])
    sample_count = len(rows)
    return {
        "samples": sample_count,
        "needs_human_review": needs_human_review,
        "labels": dict(labels),
        "dimension_labels": {key: dict(counter) for key, counter in sorted(dimension_counts.items())},
        "reasons": dict(reason_counts),
        "average_score": round(score_sum / sample_count, 4),
        "source_distribution": dict(source_distribution),
        "user_feedback_distribution": dict(feedback_distribution),
    }


def _build_markdown_report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Working Memory Evaluation Report",
            "",
            f"- samples: {summary['samples']}",
            f"- needs_human_review: {summary['needs_human_review']}",
            f"- average_score: {summary['average_score']}",
            f"- labels: {json.dumps(summary['labels'], ensure_ascii=False)}",
            f"- reasons: {json.dumps(summary['reasons'], ensure_ascii=False)}",
            f"- source_distribution: {json.dumps(summary['source_distribution'], ensure_ascii=False)}",
            f"- user_feedback_distribution: {json.dumps(summary['user_feedback_distribution'], ensure_ascii=False)}",
            "",
        ]
    )
