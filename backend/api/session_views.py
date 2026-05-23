from __future__ import annotations

import time
import uuid
from typing import Any

from context.models import ToolCall, TranscriptEntry
from context.session.session_manager import (
    DEFAULT_AGENT,
    DEFAULT_GROUP,
    DEFAULT_USER,
    SessionManager,
)


def build_session_record(
    session_manager: SessionManager,
    session_id: str,
    *,
    group_id: str = DEFAULT_GROUP,
    agent_id: str = DEFAULT_AGENT,
) -> dict[str, Any]:
    session = session_manager.get_session(session_id, group_id, agent_id)
    entries = session_manager.get_transcript(group_id, agent_id, session_id, include_compacted=True)

    latest_compaction_index: int | None = None
    compressed_context = ""
    for index, entry in enumerate(entries):
        if entry.entry_type == "compaction" and entry.content:
            latest_compaction_index = index
            compressed_context = entry.content

    start_index = (latest_compaction_index + 1) if latest_compaction_index is not None else 0
    messages: list[dict[str, Any]] = []
    for entry in entries[start_index:]:
        if entry.entry_type == "compaction":
            continue
        payload: dict[str, Any] = {
            "role": entry.role,
            "content": entry.content or "",
        }
        if entry.tool_calls:
            payload["tool_calls"] = [
                {"id": tc.id, "type": tc.type, "function": tc.function}
                for tc in entry.tool_calls
            ]
        retrieval_steps = (entry.metadata or {}).get("retrieval_steps")
        if retrieval_steps:
            payload["retrieval_steps"] = retrieval_steps
        messages.append(payload)

    metadata = session.metadata if session else {}
    title = (metadata or {}).get("title") or f"会话 {session_id[:8]}"
    created_at = session.created_at.timestamp() if session else time.time()
    updated_at = session.last_active_at.timestamp() if session else created_at
    return {
        "id": session_id,
        "title": title,
        "created_at": created_at,
        "updated_at": updated_at,
        "compressed_context": compressed_context,
        "messages": messages,
    }


def build_history_for_agent(
    session_manager: SessionManager,
    session_id: str,
    *,
    group_id: str = DEFAULT_GROUP,
    agent_id: str = DEFAULT_AGENT,
) -> list[dict[str, str]]:
    record = build_session_record(session_manager, session_id, group_id=group_id, agent_id=agent_id)
    merged: list[dict[str, str]] = []

    compressed_context = record.get("compressed_context", "").strip()
    if compressed_context:
        merged.append(
            {
                "role": "assistant",
                "content": f"[以下是之前对话的摘要]\n{compressed_context}",
            }
        )

    for message in record.get("messages", []):
        role = str(message.get("role", "assistant"))
        content = str(message.get("content", "") or "")
        if role == "assistant" and merged and merged[-1]["role"] == "assistant":
            if content:
                merged[-1]["content"] = (
                    f"{merged[-1]['content']}\n\n{content}" if merged[-1]["content"] else content
                )
            continue
        if role in {"user", "assistant"}:
            merged.append({"role": role, "content": content})

    return merged


def append_message_entry(
    session_manager: SessionManager,
    session_id: str,
    *,
    role: str,
    content: str,
    tool_calls: list[dict[str, Any]] | None = None,
    retrieval_steps: list[dict[str, Any]] | None = None,
    group_id: str = DEFAULT_GROUP,
    agent_id: str = DEFAULT_AGENT,
) -> None:
    normalized_tool_calls = None
    if tool_calls:
        normalized_tool_calls = []
        for index, tool_call in enumerate(tool_calls):
            normalized_tool_calls.append(
                ToolCall(
                    id=str(tool_call.get("id") or f"tool_{index}_{uuid.uuid4().hex[:8]}"),
                    function=(
                        tool_call["function"]
                        if isinstance(tool_call.get("function"), dict)
                        else {
                            "name": str(tool_call.get("tool") or tool_call.get("name") or "tool"),
                            "arguments": str(tool_call.get("input") or ""),
                        }
                    ),
                )
            )

    entry = TranscriptEntry(
        id=f"entry_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        group_id=group_id,
        timestamp=int(time.time() * 1000),
        role=role,  # type: ignore[arg-type]
        entry_type="normal",
        content=content,
        tool_calls=normalized_tool_calls,
        token_count=max(1, len(content or "") // 4) if content else 0,
        metadata={"retrieval_steps": retrieval_steps} if retrieval_steps else None,
    )
    session_manager.append_entry(group_id, agent_id, entry)


def update_session_title(
    session_manager: SessionManager,
    session_id: str,
    title: str,
    *,
    group_id: str = DEFAULT_GROUP,
    agent_id: str = DEFAULT_AGENT,
) -> dict[str, Any]:
    session = session_manager.get_session(session_id, group_id, agent_id)
    if session is None:
        raise KeyError(session_id)
    session.metadata = {**(session.metadata or {}), "title": title.strip() or "新会话"}
    session_manager.update_session_metadata(session_id, group_id, agent_id, session.metadata)
    return build_session_record(session_manager, session_id, group_id=group_id, agent_id=agent_id)


def create_default_session(
    session_manager: SessionManager,
    *,
    title: str,
    active_group_id: str,
    allowed_group_ids: list[str] | None,
) -> dict[str, Any]:
    metadata = {
        "title": title,
        "active_group_id": active_group_id,
        "allowed_group_ids": allowed_group_ids or [active_group_id],
    }
    session = session_manager.create_session(
        DEFAULT_GROUP,
        DEFAULT_AGENT,
        DEFAULT_USER,
        metadata=metadata,
    )
    return {
        "id": session.id,
        "title": title,
        "created_at": session.created_at.timestamp() * 1000,
        "updated_at": session.last_active_at.timestamp() * 1000,
        "message_count": 0,
    }
