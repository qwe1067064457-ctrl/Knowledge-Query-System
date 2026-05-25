"""
Shared context-domain models used by assembly, session, and registry layers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class GroupType(Enum):
    """知识库组类型"""

    LEGAL = "legal"
    MEDICAL = "medical"
    GENERAL = "general"


class SessionStatus(Enum):
    """会话状态"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


Role = Literal["user", "assistant", "tool", "system"]
EntryType = Literal["normal", "compaction", "summary", "system_notice"]
MemoryScope = Literal["user_global", "user_group", "group_shared"]
MemoryType = Literal["core", "daily_log", "domain_case"]


@dataclass
class SessionDialogueState:
    """会话级短程运行态，用于 bound query / rewrite。

    字段语义：
    - focus_question_object_*: 当前最值得继续承接的 question_object 焦点
    - focus_predicate: 当前短程 follow-up 仍在延续的谓词/属性
    - recent_question_objects: 最近仍值得作为 bound query 候选的问题对象快照
    - recent_evidence_topics: 最近证据主题摘要，用于辅助 rewrite/对齐
    - resolution_confidence: 当前 state 自身的稳定度，而不是最终回答置信度
    - last_update_reason: 最近一次 state 更新为何得出当前焦点
    """

    _CONFIDENCE_VALUES = {"high", "medium", "low"}
    _MAX_RECENT_QUESTION_OBJECTS = 6
    _MAX_RECENT_EVIDENCE_TOPICS = 6

    focus_question_object_id: Optional[str] = None
    focus_question_object_text: Optional[str] = None
    focus_predicate: Optional[str] = None
    recent_question_objects: List[Dict[str, Any]] = field(default_factory=list)
    recent_evidence_topics: List[str] = field(default_factory=list)
    resolution_confidence: str = "low"
    last_update_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        normalized = self.normalized()
        return {
            "focus_question_object_id": normalized.focus_question_object_id,
            "focus_question_object_text": normalized.focus_question_object_text,
            "focus_predicate": normalized.focus_predicate,
            "recent_question_objects": [dict(item) for item in normalized.recent_question_objects],
            "recent_evidence_topics": list(normalized.recent_evidence_topics),
            "resolution_confidence": normalized.resolution_confidence,
            "last_update_reason": normalized.last_update_reason,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SessionDialogueState":
        payload = dict(data or {})
        return cls(
            focus_question_object_id=payload.get("focus_question_object_id"),
            focus_question_object_text=payload.get("focus_question_object_text"),
            focus_predicate=payload.get("focus_predicate"),
            recent_question_objects=[dict(item) for item in payload.get("recent_question_objects", []) or []],
            recent_evidence_topics=[str(item) for item in payload.get("recent_evidence_topics", []) if item],
            resolution_confidence=str(payload.get("resolution_confidence", "low")),
            last_update_reason=payload.get("last_update_reason"),
        ).normalized()

    def normalized(self) -> "SessionDialogueState":
        recent_question_objects: List[Dict[str, Any]] = []
        seen_question_ids: set[str] = set()
        for item in self.recent_question_objects[: self._MAX_RECENT_QUESTION_OBJECTS]:
            object_id = str(item.get("object_id") or "").strip()
            content = str(item.get("content") or "").strip()
            if not object_id or not content or object_id in seen_question_ids:
                continue
            seen_question_ids.add(object_id)
            normalized_item = {
                "object_id": object_id,
                "content": content,
            }
            refs = item.get("refs")
            if isinstance(refs, (list, tuple)):
                cleaned_refs = [str(ref).strip() for ref in refs if str(ref).strip()]
                if cleaned_refs:
                    normalized_item["refs"] = cleaned_refs
            recent_question_objects.append(normalized_item)

        recent_evidence_topics: List[str] = []
        seen_topics: set[str] = set()
        for item in self.recent_evidence_topics[: self._MAX_RECENT_EVIDENCE_TOPICS]:
            topic = str(item).strip()
            if not topic or topic in seen_topics:
                continue
            seen_topics.add(topic)
            recent_evidence_topics.append(topic)

        confidence = str(self.resolution_confidence or "low").strip().lower()
        if confidence not in self._CONFIDENCE_VALUES:
            confidence = "low"

        focus_question_object_id = str(self.focus_question_object_id).strip() if self.focus_question_object_id else None
        focus_question_object_text = str(self.focus_question_object_text).strip() if self.focus_question_object_text else None
        focus_predicate = str(self.focus_predicate).strip() if self.focus_predicate else None
        last_update_reason = str(self.last_update_reason).strip() if self.last_update_reason else None

        if focus_question_object_id and not any(
            item.get("object_id") == focus_question_object_id for item in recent_question_objects
        ):
            if focus_question_object_text:
                recent_question_objects.insert(
                    0,
                    {
                        "object_id": focus_question_object_id,
                        "content": focus_question_object_text,
                    },
                )
                recent_question_objects = recent_question_objects[: self._MAX_RECENT_QUESTION_OBJECTS]
            else:
                focus_question_object_id = None

        if not focus_question_object_id:
            focus_question_object_text = None

        return SessionDialogueState(
            focus_question_object_id=focus_question_object_id,
            focus_question_object_text=focus_question_object_text,
            focus_predicate=focus_predicate,
            recent_question_objects=recent_question_objects,
            recent_evidence_topics=recent_evidence_topics,
            resolution_confidence=confidence,
            last_update_reason=last_update_reason,
        )


@dataclass
class ToolCall:
    """工具调用"""

    id: str
    type: Literal["function"] = "function"
    function: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptEntry:
    """转录条目：客观、完整的系统活动日志。"""

    id: str
    session_id: str
    group_id: str
    timestamp: int
    role: Role
    entry_type: EntryType
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    token_count: Optional[int] = None
    in_reply_to: Optional[str] = None
    model_name: Optional[str] = None
    latency_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "session_id": self.session_id,
            "group_id": self.group_id,
            "timestamp": self.timestamp,
            "role": self.role,
            "entry_type": self.entry_type,
            "content": self.content,
            "token_count": self.token_count,
        }
        if self.tool_calls:
            result["tool_calls"] = [
                {"id": tc.id, "type": tc.type, "function": tc.function}
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.in_reply_to:
            result["in_reply_to"] = self.in_reply_to
        if self.model_name:
            result["model_name"] = self.model_name
        if self.latency_ms:
            result["latency_ms"] = self.latency_ms
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptEntry":
        tool_calls = None
        if "tool_calls" in data and data["tool_calls"]:
            tool_calls = [
                ToolCall(id=tc["id"], type=tc["type"], function=tc["function"])
                for tc in data["tool_calls"]
            ]
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            group_id=data["group_id"],
            timestamp=data["timestamp"],
            role=data["role"],
            entry_type=data.get("entry_type", "normal"),
            content=data.get("content"),
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
            token_count=data.get("token_count"),
            in_reply_to=data.get("in_reply_to"),
            model_name=data.get("model_name"),
            latency_ms=data.get("latency_ms"),
            metadata=data.get("metadata"),
        )


@dataclass
class Session:
    """会话元数据"""

    id: str
    group_id: str
    user_id: str
    agent_id: str
    created_at: datetime
    last_active_at: datetime
    archived_at: Optional[datetime] = None
    status: SessionStatus = SessionStatus.ACTIVE
    turn_count: int = 0
    total_tokens: int = 0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "last_active_at": self.last_active_at.isoformat() if isinstance(self.last_active_at, datetime) else self.last_active_at,
            "archived_at": self.archived_at.isoformat() if self.archived_at and isinstance(self.archived_at, datetime) else self.archived_at,
            "status": self.status.value if isinstance(self.status, SessionStatus) else self.status,
            "turn_count": self.turn_count,
            "total_tokens": self.total_tokens,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        created_at = data["created_at"]
        last_active_at = data["last_active_at"]
        archived_at = data.get("archived_at")

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif isinstance(created_at, (int, float)):
            created_at = datetime.fromtimestamp(created_at / 1000 if created_at > 1e10 else created_at)

        if isinstance(last_active_at, str):
            last_active_at = datetime.fromisoformat(last_active_at)
        elif isinstance(last_active_at, (int, float)):
            last_active_at = datetime.fromtimestamp(last_active_at / 1000 if last_active_at > 1e10 else last_active_at)

        if archived_at:
            if isinstance(archived_at, str):
                archived_at = datetime.fromisoformat(archived_at)
            elif isinstance(archived_at, (int, float)):
                archived_at = datetime.fromtimestamp(archived_at / 1000 if archived_at > 1e10 else archived_at)

        status = data.get("status", "active")
        if isinstance(status, str):
            status = SessionStatus(status)

        return cls(
            id=data["id"],
            group_id=data["group_id"],
            user_id=data["user_id"],
            agent_id=data["agent_id"],
            created_at=created_at,
            last_active_at=last_active_at,
            archived_at=archived_at,
            status=status,
            turn_count=data.get("turn_count", 0),
            total_tokens=data.get("total_tokens", 0),
            metadata=data.get("metadata"),
        )


@dataclass
class MemoryEntry:
    """记忆条目"""

    content: str
    source: str
    group_id: str
    timestamp: datetime
    score: float = 0.0
    scope: MemoryScope = "user_group"
    memory_type: MemoryType = "daily_log"
    user_id: Optional[str] = None
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    source_session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
