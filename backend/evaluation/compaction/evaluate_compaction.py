from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.compaction.topic_config import build_topic_config  # noqa: E402
from evaluation.core.case_loader import load_jsonl_cases  # noqa: E402
from evaluation.core.runner import evaluate_topic_cases, run_topic_evaluation  # noqa: E402


ALLOWED_SOURCES = {"offline_seed", "offline_replay", "online_sample"}
ALLOWED_FEEDBACK = {"like", "dislike", None}


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl_cases(path)


def validate_case(case: dict[str, Any]) -> None:
    required_fields = {
        "case_id",
        "trace_id",
        "source",
        "pre_compaction_summary",
        "post_compaction_summary",
        "pre_compaction_extraction_summary",
        "expected_anchor_required",
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
    for key in ("pre_compaction_summary", "post_compaction_summary", "pre_compaction_extraction_summary"):
        if not isinstance(case[key], dict):
            raise ValueError(f"{key} must be an object")
    if not isinstance(case["expected_anchor_required"], bool):
        raise ValueError("expected_anchor_required must be a boolean")


def evaluate_case(
    case: dict[str, Any],
    *,
    semantic_labels: dict[str, str] | None = None,
    llm_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_case(case)
    config = build_topic_config(
        use_llm=False,
        label_overrides={case["case_id"]: semantic_labels or {}},
        llm_metadata_overrides={case["case_id"]: llm_metadata or {}},
    )
    return evaluate_topic_cases([case], config=config)[0]


def evaluate_cases(
    cases: Iterable[dict[str, Any]],
    *,
    use_llm: bool = False,
    label_overrides: dict[str, dict[str, str]] | None = None,
    llm_metadata_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = list(cases)
    for case in rows:
        validate_case(case)
    config = build_topic_config(
        use_llm=use_llm,
        label_overrides=label_overrides,
        llm_metadata_overrides=llm_metadata_overrides,
    )
    return [dict(item) for item in evaluate_topic_cases(rows, config=config)]


def write_report(report_dir: str | Path, *, results: Iterable[dict[str, Any]], summary: dict[str, Any]) -> None:
    config = build_topic_config(use_llm=False)
    actual_summary = config.report_writer.write(list(results), report_dir)
    if actual_summary != summary:
        raise ValueError("Provided summary does not match report writer output")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate compaction preservation cases.")
    parser.add_argument("cases", type=Path, help="JSONL file or directory that contains case rows.")
    parser.add_argument("--report-dir", type=Path, default=None, help="Optional directory for summary outputs.")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM grader for semantic dimensions.")
    args = parser.parse_args()

    config = build_topic_config(use_llm=args.use_llm)
    _, summary = run_topic_evaluation(args.cases, config=config, report_dir=args.report_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
