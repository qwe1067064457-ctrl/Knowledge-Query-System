from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from memory_system.session_working_memory.models import WorkingMemoryEntry


class SessionWorkingMemoryWriter:
    _TASK_HINTS = ("核验", "比较", "检查", "判断", "确认", "解释", "质疑", "依据")
    _ASSERTION_HINTS = ("不对", "有问题", "漏了", "没有处理", "依据不足", "不成立", "错了")
    _ANSWER_HINTS = ("是", "不是", "属于", "不属于", "成立", "不成立", "可以", "不可以", "依据", "结论")

    def build_entries_from_turn(
        self,
        *,
        turn_id: str,
        user_query: str,
        answer_text: str | None = None,
        current_goal: str | None = None,
        binding_result: dict[str, Any] | None = None,
        review_result: dict[str, Any] | None = None,
    ) -> list[WorkingMemoryEntry]:
        entries: list[WorkingMemoryEntry] = []
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

        task_text = (current_goal or "").strip()
        if not task_text and any(token in user_query for token in self._TASK_HINTS):
            task_text = user_query.strip()
        if task_text:
            entries.append(
                WorkingMemoryEntry(
                    entry_id=f"{turn_id}:focus_task",
                    entry_type="focus_task",
                    turn_id=turn_id,
                    source_kind="user_query",
                    source_ref=f"{turn_id}:user",
                    content=task_text,
                    confidence="high",
                    created_at=timestamp,
                )
            )

        rewritten_query = str((binding_result or {}).get("rewritten_query") or "").strip()
        if rewritten_query and rewritten_query != user_query.strip():
            entries.append(
                WorkingMemoryEntry(
                    entry_id=f"{turn_id}:resolved_query",
                    entry_type="resolved_query",
                    turn_id=turn_id,
                    source_kind="binding",
                    source_ref=f"{turn_id}:binding",
                    content=rewritten_query,
                    structured_payload={
                        "resolved_target_ids": list((binding_result or {}).get("resolved_target_ids", ()) or ()),
                    },
                    confidence=str((binding_result or {}).get("binding_confidence") or "medium"),
                    created_at=timestamp,
                )
            )

        for index, unit in enumerate(self._extract_answer_units(answer_text or ""), start=1):
            entries.append(
                WorkingMemoryEntry(
                    entry_id=f"{turn_id}:answer_unit:{index}",
                    entry_type="answer_unit",
                    turn_id=turn_id,
                    source_kind="answer",
                    source_ref=f"{turn_id}:answer:{index}",
                    content=unit,
                    structured_payload={"unit_index": index},
                    confidence="high",
                    created_at=timestamp,
                )
            )

        for index, assertion in enumerate(self._extract_user_assertions(user_query), start=1):
            entries.append(
                WorkingMemoryEntry(
                    entry_id=f"{turn_id}:user_assertion:{index}",
                    entry_type="user_assertion",
                    turn_id=turn_id,
                    source_kind="user_query",
                    source_ref=f"{turn_id}:user_assertion:{index}",
                    content=assertion,
                    confidence="high",
                    created_at=timestamp,
                )
            )

        review_status = str((review_result or {}).get("status") or "").strip()
        if review_status:
            review_content = str((review_result or {}).get("summary") or review_status).strip()
            entries.append(
                WorkingMemoryEntry(
                    entry_id=f"{turn_id}:review_outcome",
                    entry_type="review_outcome",
                    turn_id=turn_id,
                    source_kind="review",
                    source_ref=f"{turn_id}:review",
                    content=review_content,
                    structured_payload={"status": review_status},
                    confidence="high",
                    created_at=timestamp,
                )
            )
        return entries

    def _extract_answer_units(self, answer_text: str) -> list[str]:
        segments = [segment.strip() for segment in re.split(r"[\n。！？!?；;]+", answer_text) if segment.strip()]
        return [
            segment
            for segment in segments
            if len(segment) >= 8 and any(token in segment for token in self._ANSWER_HINTS)
        ][:4]

    def _extract_user_assertions(self, user_query: str) -> list[str]:
        if not any(token in user_query for token in self._ASSERTION_HINTS):
            return []
        clauses = [clause.strip() for clause in re.split(r"[，。！？!?；;]+", user_query) if clause.strip()]
        return [clause for clause in clauses if any(token in clause for token in self._ASSERTION_HINTS)][:3]

