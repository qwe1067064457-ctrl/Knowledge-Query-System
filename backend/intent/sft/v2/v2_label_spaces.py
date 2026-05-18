from __future__ import annotations

from typing import Any

MULTICLASS_HEADS: dict[str, tuple[str, ...]] = {
    "main_intent": ("qa", "chat", "system", "unsupported"),
    "task_complexity": ("simple", "compound", "complex"),
    "task_shape": ("none", "single_question", "verify", "compare", "summarize", "multi_question", "mixed"),
    "task_topology": ("single", "parallel_queries", "parallel_subtasks", "staged"),
}

MULTILABEL_HEADS: dict[str, tuple[str, ...]] = {
    "modifiers": (
        "follow_up",
        "challenge",
        "soft_doubt",
        "ask_source",
        "ask_capability",
        "needs_clarification",
        "out_of_scope",
    ),
    "context": (
        "history_reference",
        "needs_previous_answer",
        "previous_retrieval",
        "clarify_hint",
    ),
    "safety": (
        "unsupported",
        "out_of_scope",
    ),
}

DEFAULT_LABEL_SPACES: dict[str, tuple[str, ...]] = {
    **MULTICLASS_HEADS,
    **MULTILABEL_HEADS,
}


def build_label_space_manifest() -> dict[str, Any]:
    return {
        "multiclass_heads": {name: list(labels) for name, labels in MULTICLASS_HEADS.items()},
        "multilabel_heads": {name: list(labels) for name, labels in MULTILABEL_HEADS.items()},
    }


def label_to_index(labels: tuple[str, ...]) -> dict[str, int]:
    return {label: index for index, label in enumerate(labels)}
