from __future__ import annotations


UNIT_OUTPUT_SCHEMAS = {
    "QaLikeResultPayload",
    "ChatLikeResultPayload",
    "RejectLikeResultPayload",
    "CompareResultPayload",
    "VerifyResultPayload",
    "SynthesisResultPayload",
}


def validate_unit_output_schema(name: str) -> str:
    if name not in UNIT_OUTPUT_SCHEMAS:
        raise ValueError(f"unknown unit output schema: {name}")
    return name
