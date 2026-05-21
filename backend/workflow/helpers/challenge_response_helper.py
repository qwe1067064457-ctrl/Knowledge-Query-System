from __future__ import annotations

from typing import Any


class ChallengeResponseHelper:
    def build_clarification_question(
        self,
        *,
        query: str,
        bound_targets: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    ) -> str:
        if bound_targets:
            labels = [str(item.get("content") or item.get("object_id") or "").strip() for item in bound_targets]
            labels = [label for label in labels if label]
            if labels:
                return f"你现在是在质疑 {labels[0]} 这一点，还是在追问它的依据来源？"
        return "你现在是在质疑上一条结论本身，还是想让我补充它的依据来源？"

    def build_evidence_fallback_message(
        self,
        *,
        query: str,
        targets: tuple[dict[str, Any], ...] | list[dict[str, Any]],
        evidence_refs: list[str],
    ) -> str:
        labels = [str(item.get("content") or item.get("object_id") or "").strip() for item in targets]
        labels = [label for label in labels if label]
        joined = "、".join(labels[:2]) if labels else "当前质疑目标"
        if evidence_refs:
            return f"现有证据已覆盖 {joined} 的一部分背景，但还不足以稳定完成复核结论。"
        return f"当前还没有足够证据支持对 {joined} 做稳定复核，需要补充更多依据。"
