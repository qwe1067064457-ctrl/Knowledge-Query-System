from __future__ import annotations

from typing import Any

from evaluation.intent.v2_migration import infer_signal_buckets_from_v1

EXPECTED_BUCKETS = ("intent", "task", "context_fact", "safety")

ALLOWED_MULTI_BUCKET_SIGNALS: dict[str, tuple[str, ...]] = {}

KNOWN_SIGNALS: dict[str, tuple[str, ...]] = {
    "intent": (
        "qa",
        "chat",
        "system",
        "ask_capability",
        "scope_question",
        "follow_up",
        "ask_source",
        "challenge",
        "soft_doubt",
    ),
    "task": (
        "multi_question",
        "parallel_subtasks",
        "staged",
        "complex",
    ),
    "context_fact": (
        "history_reference",
        "needs_previous_answer",
        "previous_retrieval",
        "missing_reference_target",
        "possibly_ambiguous",
        "needs_context_check",
    ),
    "safety": (
        "unsupported",
        "out_of_scope",
    ),
}


def normalize_signal_buckets(evidence: dict[str, Any]) -> dict[str, list[str]]:
    raw = evidence.get("signal_buckets")
    if raw is None:
        raw = infer_signal_buckets_from_v1(evidence)
    normalized: dict[str, list[str]] = {}
    for bucket in EXPECTED_BUCKETS:
        if bucket == "context_fact":
            values = []
            if isinstance(raw, dict):
                values = raw.get("context_fact", raw.get("context", []))
        else:
            values = raw.get(bucket, []) if isinstance(raw, dict) else []
        normalized[bucket] = _ordered_unique(str(value) for value in values if value)
    return normalized


def flatten_signal_buckets(signal_buckets: dict[str, list[str]]) -> list[str]:
    ordered: list[str] = []
    for bucket in EXPECTED_BUCKETS:
        for signal in signal_buckets.get(bucket, []):
            if signal not in ordered:
                ordered.append(signal)
    return ordered


def find_unknown_signals(signal_buckets: dict[str, list[str]]) -> dict[str, list[str]]:
    unknown: dict[str, list[str]] = {}
    for bucket in EXPECTED_BUCKETS:
        known = set(KNOWN_SIGNALS[bucket])
        bucket_unknown = [signal for signal in signal_buckets.get(bucket, []) if signal not in known]
        if bucket_unknown:
            unknown[bucket] = bucket_unknown
    return unknown


def find_cross_bucket_conflicts(signal_buckets: dict[str, list[str]]) -> dict[str, list[str]]:
    locations: dict[str, list[str]] = {}
    for bucket in EXPECTED_BUCKETS:
        for signal in signal_buckets.get(bucket, []):
            locations.setdefault(signal, []).append(bucket)
    return {
        signal: buckets
        for signal, buckets in locations.items()
        if len(buckets) > 1
    }


def split_cross_bucket_conflicts(
    signal_buckets: dict[str, list[str]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    conflicts = find_cross_bucket_conflicts(signal_buckets)
    allowed: dict[str, list[str]] = {}
    violations: dict[str, list[str]] = {}
    for signal, buckets in conflicts.items():
        expected = ALLOWED_MULTI_BUCKET_SIGNALS.get(signal)
        ordered_buckets = tuple(sorted(buckets))
        if expected and ordered_buckets == tuple(sorted(expected)):
            allowed[signal] = list(buckets)
        else:
            violations[signal] = list(buckets)
    return allowed, violations


def _ordered_unique(values: Any) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered
