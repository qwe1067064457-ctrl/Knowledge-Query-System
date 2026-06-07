from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .case_loader import load_jsonl_cases
from .finalizer import Finalizer
from .model_evaluator import ModelEvaluator
from .report_writer import ReportWriter
from .rule_evaluator import RuleEvaluator
from .types import EvalCase, FinalEvalResult


@dataclass(frozen=True)
class TopicRunnerConfig:
    topic: str
    rule_evaluator: RuleEvaluator
    finalizer: Finalizer
    report_writer: ReportWriter
    model_evaluator: ModelEvaluator | None = None
    case_loader: Callable[[str | Path], list[dict[str, Any]]] = load_jsonl_cases


def evaluate_topic_cases(
    cases: Iterable[EvalCase],
    *,
    config: TopicRunnerConfig,
) -> list[FinalEvalResult]:
    results: list[FinalEvalResult] = []
    for raw_case in cases:
        case = dict(raw_case)
        case.setdefault("topic", config.topic)
        rule_result = config.rule_evaluator.evaluate(case)
        model_result = config.model_evaluator.evaluate(case) if config.model_evaluator is not None else None
        results.append(
            config.finalizer.finalize(
                case,
                rule_result=rule_result,
                model_result=model_result,
            )
        )
    return results


def run_topic_evaluation(
    cases_path: str | Path,
    *,
    config: TopicRunnerConfig,
    report_dir: str | Path | None = None,
) -> tuple[list[FinalEvalResult], dict[str, Any]]:
    cases = config.case_loader(cases_path)
    results = evaluate_topic_cases(cases, config=config)
    if report_dir is not None:
        summary = config.report_writer.write(results, report_dir)
    else:
        summary = config.report_writer.summarize(results)
    return results, summary
