from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


UnitCapability = Literal["qa_like", "chat_like", "reject_like", "compare", "verify", "synthesis"]

FORBIDDEN_REACT_TOOLS = {
    "target_resolution",
    "relevant_set_selection",
    "challenge_target_selection",
    "evidence_check",
    "target_evidence_check",
    "challenge_re_evaluate",
    "question_boundary_detector",
    "dependency_resolver",
    "decomposition",
    "planning",
    "route_selection",
    "llm_adjudication",
    "retrieval_execute",
    "terminal",
    "python_repl",
    "read_file",
    "fetch_url",
}


@dataclass(frozen=True)
class UnitRuntimeConfig:
    capability: UnitCapability
    react_enabled: bool
    tools: tuple[str, ...]
    output_schema: str

    def validate(self) -> None:
        forbidden = sorted(set(self.tools) & FORBIDDEN_REACT_TOOLS)
        if forbidden:
            raise ValueError(f"unit runtime config exposes forbidden tools: {', '.join(forbidden)}")


UNIT_RUNTIME_CONFIG: dict[str, UnitRuntimeConfig] = {
    "qa_like": UnitRuntimeConfig(
        capability="qa_like",
        react_enabled=False,
        tools=("query_rewrite", "evidence_anchor", "caution_assembly"),
        output_schema="QaLikeResultPayload",
    ),
    "chat_like": UnitRuntimeConfig(
        capability="chat_like",
        react_enabled=False,
        tools=(),
        output_schema="ChatLikeResultPayload",
    ),
    "reject_like": UnitRuntimeConfig(
        capability="reject_like",
        react_enabled=False,
        tools=("answer_constraint", "caution_assembly"),
        output_schema="RejectLikeResultPayload",
    ),
    "compare": UnitRuntimeConfig(
        capability="compare",
        react_enabled=True,
        tools=("evidence_anchor", "caution_assembly", "answer_constraint"),
        output_schema="CompareResultPayload",
    ),
    "verify": UnitRuntimeConfig(
        capability="verify",
        react_enabled=True,
        tools=("query_rewrite", "evidence_anchor", "answer_constraint", "caution_assembly"),
        output_schema="VerifyResultPayload",
    ),
    "synthesis": UnitRuntimeConfig(
        capability="synthesis",
        react_enabled=True,
        tools=("finding_projection", "evidence_anchor", "caution_assembly", "answer_constraint"),
        output_schema="SynthesisResultPayload",
    ),
}


def get_unit_runtime_config(capability: str) -> UnitRuntimeConfig:
    try:
        config = UNIT_RUNTIME_CONFIG[capability]
    except KeyError as exc:
        raise ValueError(f"unknown unit capability: {capability}") from exc
    config.validate()
    return config


def tool_names_for_unit(capability: str) -> tuple[str, ...]:
    return get_unit_runtime_config(capability).tools
