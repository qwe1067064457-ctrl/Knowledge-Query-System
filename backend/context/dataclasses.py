"""
数据类定义 - 会话管理、记忆系统与上下文管理模块
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from enum import Enum


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


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    type: Literal["function"] = "function"
    function: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptEntry:
    """
    转录条目：客观、完整的系统活动日志

    包含用户消息、助手回复、工具调用、系统通知、压缩记录等所有内容
    """
    id: str
    session_id: str
    group_id: str
    timestamp: int  # 毫秒时间戳

    role: Role
    entry_type: EntryType

    # 内容字段（根据role选择性使用）
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None

    # Token 计数
    token_count: Optional[int] = None

    # 扩展字段
    in_reply_to: Optional[str] = None
    model_name: Optional[str] = None
    latency_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
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
    def from_dict(cls, data: Dict[str, Any]) -> TranscriptEntry:
        """从字典创建"""
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
            metadata=data.get("metadata")
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

    # 统计字段
    turn_count: int = 0
    total_tokens: int = 0

    # 扩展
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
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
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Session:
        """从字典创建"""
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
            metadata=data.get("metadata")
        )


@dataclass
class MemoryEntry:
    """记忆条目"""
    content: str
    source: str  # "MEMORY.md" 或 "memory/2026-04-27.md"
    group_id: str
    timestamp: datetime
    score: float = 0.0