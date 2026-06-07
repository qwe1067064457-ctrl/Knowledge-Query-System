from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.core.case_loader import load_jsonl_cases  # noqa: E402
from evaluation.core.runner import evaluate_topic_cases, run_topic_evaluation  # noqa: E402
from evaluation.workflow_answer.topic_config import build_topic_config, summarize_results  # noqa: E402


ALLOWED_SOURCES = {"offline_seed", "offline_replay", "online_sample"}
ALLOWED_FEEDBACK = {"like", "dislike", None}


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl_cases(path)


def save_results_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    target.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def validate_case(case: dict[str, Any]) -> None:
    required_fields = {
        "case_id",
        "trace_id",
        "source",
        "user_query",
        "knowledge_evidence_summary",
        "retrieval_summary",
        "workflow_summary",
        "answer_text",
        "core_summary_present",
        "user_feedback",
    }
    missing = sorted(required_fields - set(case))
    if missing:
        raise ValueError(f"Case missing required fields: {', '.join(missing)}")

    if case["source"] not in ALLOWED_SOURCES:
        raise ValueError(f"Unsupported case source: {case['source']}")
    if case["user_feedback"] not in ALLOWED_FEEDBACK:
        raise ValueError(f"Unsupported user_feedback: {case['user_feedback']}")

    if not isinstance(case["case_id"], str) or not case["case_id"].strip():
        raise ValueError("case_id must be a non-empty string")
    if not isinstance(case["trace_id"], str) or not case["trace_id"].strip():
        raise ValueError("trace_id must be a non-empty string")
    if not isinstance(case["user_query"], str) or not case["user_query"].strip():
        raise ValueError("user_query must be a non-empty string")
    if not isinstance(case["answer_text"], str) or not case["answer_text"].strip():
        raise ValueError("answer_text must be a non-empty string")

    for key in ("knowledge_evidence_summary", "retrieval_summary", "workflow_summary"):
        if not isinstance(case[key], dict):
            raise ValueError(f"{key} must be an object")
    if not isinstance(case["core_summary_present"], bool):
        raise ValueError("core_summary_present must be a boolean")


def build_case_from_trace_events(
    events: Iterable[dict[str, Any] | Any],
    *,
    source: str = "offline_replay",
    case_id: str | None = None,
    answer_text: str | None = None,
    user_feedback: str | None = None,
) -> dict[str, Any]:
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"Unsupported case source: {source}")
    if user_feedback not in ALLOWED_FEEDBACK:
        raise ValueError(f"Unsupported user_feedback: {user_feedback}")

    normalized = [_event_to_dict(item) for item in events]
    if not normalized:
        raise ValueError("At least one event is required to build a case")

    by_type = {str(item.get("event_type") or ""): item for item in normalized}
    trace_ids = {str(item.get("trace_id") or "") for item in normalized if item.get("trace_id")}
    if len(trace_ids) != 1:
        raise ValueError("Trace events must share exactly one trace_id")
    trace_id = next(iter(trace_ids))

    retrieval_event = by_type.get("retrieval_run", {})
    answer_event = by_type.get("answer_model_run", {})
    workflow_event = by_type.get("workflow_run", {})
    context_event = by_type.get("context_assembly_run", {})

    retrieval_input = _as_dict(retrieval_event.get("input_summary"))
    retrieval_output = _as_dict(retrieval_event.get("output_summary"))
    answer_input = _as_dict(answer_event.get("input_summary"))
    answer_output = _as_dict(answer_event.get("output_summary"))
    answer_metadata = _as_dict(answer_event.get("metadata"))
    workflow_output = _as_dict(workflow_event.get("output_summary"))
    context_output = _as_dict(context_event.get("output_summary"))

    user_query = (
        str(retrieval_input.get("query") or "").strip()
        or str(answer_metadata.get("final_user_query") or "").strip()
        or str(_as_dict(answer_input.get("messages_summary")).get("latest_user_query") or "").strip()
        or str(_as_dict(workflow_event.get("input_summary")).get("user_query") or "").strip()
    )
    resolved_answer_text = (
        answer_text
        or str(answer_output.get("answer_text") or "").strip()
        or str(answer_event.get("answer_text") or "").strip()
    )

    core_present = bool(context_output.get("core_block_present"))
    if not core_present:
        for block in answer_metadata.get("memory_block_types", []) or []:
            if "core" in str(block).lower():
                core_present = True
                break

    case = {
        "case_id": case_id or trace_id,
        "trace_id": trace_id,
        "source": source,
        "user_query": user_query,
        "knowledge_evidence_summary": _as_dict(
            retrieval_output.get("evidence_summary") or workflow_output.get("evidence_summary")
        ),
        "retrieval_summary": retrieval_output,
        "workflow_summary": workflow_output,
        "answer_text": resolved_answer_text,
        "core_summary_present": core_present,
        "user_feedback": user_feedback,
    }
    return case


def evaluate_case(
    case: dict[str, Any],
    *,
    retrieval_semantic_labels: dict[str, str] | None = None,
    answer_semantic_labels: dict[str, str] | None = None,
    retrieval_llm_metadata: dict[str, Any] | None = None,
    answer_llm_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_case(case)
    config = build_topic_config(
        use_llm=False,
        retrieval_label_overrides={case["case_id"]: retrieval_semantic_labels or {}},
        answer_label_overrides={case["case_id"]: answer_semantic_labels or {}},
        retrieval_llm_metadata={case["case_id"]: retrieval_llm_metadata or {}},
        answer_llm_metadata={case["case_id"]: answer_llm_metadata or {}},
    )
    return evaluate_topic_cases([case], config=config)[0]


def run_rule_layer(case: dict[str, Any]) -> dict[str, Any]:
    validate_case(case)
    return build_topic_config(use_llm=False).rule_evaluator.evaluate(case)


def run_model_layer(
    case: dict[str, Any],
    *,
    llm_runtime: WorkflowAnswerLLMRuntime | None,
    case_id: str,
    retrieval_label_overrides: dict[str, dict[str, str]] | None,
    answer_label_overrides: dict[str, dict[str, str]] | None,
    retrieval_llm_metadata: dict[str, dict[str, Any]] | None,
    answer_llm_metadata: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    config = build_topic_config(
        use_llm=llm_runtime is not None,
        retrieval_label_overrides=retrieval_label_overrides,
        answer_label_overrides=answer_label_overrides,
        retrieval_llm_metadata=retrieval_llm_metadata,
        answer_llm_metadata=answer_llm_metadata,
    )
    return config.model_evaluator.evaluate(case) if config.model_evaluator is not None else {}


def finalize_result(
    case: dict[str, Any],
    *,
    rule_result: dict[str, Any],
    model_result: dict[str, Any],
) -> dict[str, Any]:
    config = build_topic_config(use_llm=False)
    return config.finalizer.finalize(
        case,
        rule_result=rule_result,
        model_result=model_result,
    )


def evaluate_cases(
    cases: Iterable[dict[str, Any]],
    *,
    use_llm: bool = False,
    retrieval_label_overrides: dict[str, dict[str, str]] | None = None,
    answer_label_overrides: dict[str, dict[str, str]] | None = None,
    retrieval_llm_metadata: dict[str, dict[str, Any]] | None = None,
    answer_llm_metadata: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = list(cases)
    config = build_topic_config(
        use_llm=use_llm,
        retrieval_label_overrides=retrieval_label_overrides,
        answer_label_overrides=answer_label_overrides,
        retrieval_llm_metadata=retrieval_llm_metadata,
        answer_llm_metadata=answer_llm_metadata,
    )
    for case in rows:
        validate_case(case)
    return [dict(item) for item in evaluate_topic_cases(rows, config=config)]


def write_report(report_dir: str | Path, *, results: Iterable[dict[str, Any]], summary: dict[str, Any]) -> None:
    config = build_topic_config(use_llm=False)
    rows = list(results)
    actual_summary = config.report_writer.write(rows, report_dir)
    if actual_summary != summary:
        raise ValueError("Provided summary does not match report writer output")


def _event_to_dict(item: dict[str, Any] | Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "to_dict"):
        payload = item.to_dict()
        if isinstance(payload, dict):
            return payload
    raise TypeError("Trace event must be a dict or expose to_dict()")


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate workflow retrieval + answer cases.")
    parser.add_argument("cases", type=Path, help="JSONL file or directory that contains case rows.")
    parser.add_argument("--report-dir", type=Path, default=None, help="Optional directory for summary outputs.")
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use the existing backend LLM infrastructure to score semantic dimensions in parallel with rules.",
    )
    args = parser.parse_args()

    config = build_topic_config(use_llm=args.use_llm)
    results, summary = run_topic_evaluation(args.cases, config=config, report_dir=args.report_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
