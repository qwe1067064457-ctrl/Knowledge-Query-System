from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.workflow_answer.finalize_layer.adjudication_router import (  # noqa: E402
    route_human_review,
)
from evaluation.workflow_answer.finalize_layer.aggregation import finalize_case_result  # noqa: E402
from evaluation.workflow_answer.model_layer.llm_runtime import WorkflowAnswerLLMRuntime  # noqa: E402
from evaluation.workflow_answer.rule_layer.answer_rules import grade_answer_case  # noqa: E402
from evaluation.workflow_answer.rule_layer.retrieval_rules import (  # noqa: E402
    grade_retrieval_case,
)


ALLOWED_SOURCES = {"offline_seed", "offline_replay", "online_sample"}
ALLOWED_FEEDBACK = {"like", "dislike", None}


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    root = Path(path)
    if root.is_dir():
        paths = sorted(root.glob("*.jsonl"))
    else:
        paths = [root]

    rows: list[dict[str, Any]] = []
    for case_path in paths:
        for line_no, line in enumerate(case_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Case line must be an object: {case_path}:{line_no}")
            rows.append(payload)
    return rows


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
    retrieval_rule = grade_retrieval_case(case)
    answer_rule = grade_answer_case(case)
    retrieval, answer, finalize_meta = finalize_case_result(
        case=case,
        retrieval_rule=retrieval_rule,
        answer_rule=answer_rule,
        retrieval_model_labels=retrieval_semantic_labels,
        answer_model_labels=answer_semantic_labels,
    )

    grader_metadata = {
        "rule_result_meta": {
            "retrieval": retrieval_rule["metadata"],
            "answer": answer_rule["metadata"],
        },
        "model_result_meta": {
            "retrieval": retrieval_llm_metadata or {},
            "answer": answer_llm_metadata or {},
        },
        "finalize_meta": {
            **finalize_meta,
            "policy": {
                "mode": "parallel_merge",
                "llm_failure_fallback": "rule_labels",
            },
            "retrieval_final_meta": retrieval.pop("metadata"),
            "answer_final_meta": answer.pop("metadata"),
        },
    }

    result = {
        "case_id": case["case_id"],
        "trace_id": case["trace_id"],
        "source": case["source"],
        "user_feedback": case["user_feedback"],
        "retrieval": retrieval,
        "answer": answer,
        "grader_metadata": grader_metadata,
    }
    adjudication = route_human_review(case=case, result=result)
    result["needs_human_review"] = adjudication["needs_human_review"]
    result["human_review_reasons"] = adjudication["reasons"]
    result["review_priority"] = adjudication["priority"]
    return result


def run_rule_layer(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "retrieval": grade_retrieval_case(case),
        "answer": grade_answer_case(case),
    }


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
    if llm_runtime is None:
        return {
            "retrieval_labels": (retrieval_label_overrides or {}).get(case_id),
            "answer_labels": (answer_label_overrides or {}).get(case_id),
            "retrieval_meta": (retrieval_llm_metadata or {}).get(case_id, {}),
            "answer_meta": (answer_llm_metadata or {}).get(case_id, {}),
        }

    try:
        runtime_labels = llm_runtime.grade_case(case)
    except Exception as exc:
        runtime_labels = {
            "retrieval": {"labels": {}, "responses": {}, "error": str(exc)},
            "answer": {"labels": {}, "responses": {}, "error": str(exc)},
        }

    return {
        "retrieval_labels": (retrieval_label_overrides or {}).get(case_id)
        or runtime_labels.get("retrieval", {}).get("labels"),
        "answer_labels": (answer_label_overrides or {}).get(case_id)
        or runtime_labels.get("answer", {}).get("labels"),
        "retrieval_meta": (retrieval_llm_metadata or {}).get(case_id)
        or runtime_labels.get("retrieval", {}),
        "answer_meta": (answer_llm_metadata or {}).get(case_id)
        or runtime_labels.get("answer", {}),
    }


def finalize_result(
    case: dict[str, Any],
    *,
    rule_result: dict[str, Any],
    model_result: dict[str, Any],
) -> dict[str, Any]:
    return evaluate_case(
        case,
        retrieval_semantic_labels=model_result.get("retrieval_labels"),
        answer_semantic_labels=model_result.get("answer_labels"),
        retrieval_llm_metadata=model_result.get("retrieval_meta"),
        answer_llm_metadata=model_result.get("answer_meta"),
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
    llm_runtime = WorkflowAnswerLLMRuntime() if use_llm else None
    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("case_id") or "")
        rule_result = run_rule_layer(case)
        model_result = run_model_layer(
            case,
            llm_runtime=llm_runtime,
            case_id=case_id,
            retrieval_label_overrides=retrieval_label_overrides,
            answer_label_overrides=answer_label_overrides,
            retrieval_llm_metadata=retrieval_llm_metadata,
            answer_llm_metadata=answer_llm_metadata,
        )
        results.append(finalize_result(case, rule_result=rule_result, model_result=model_result))
    return results


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


def write_report(report_dir: str | Path, *, results: Iterable[dict[str, Any]], summary: dict[str, Any]) -> None:
    target_dir = Path(report_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    rows = list(results)
    save_results_jsonl(target_dir / "results.jsonl", rows)
    (target_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (target_dir / "report.md").write_text(_build_markdown_report(summary), encoding="utf-8")


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

    cases = load_cases(args.cases)
    results = evaluate_cases(cases, use_llm=args.use_llm)
    summary = summarize_results(results)
    if args.report_dir:
        write_report(args.report_dir, results=results, summary=summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
