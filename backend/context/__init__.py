"""
context 模块 - 会话管理、记忆系统与上下文管理
"""
from context.dataclasses import (
    GroupType,
    SessionStatus,
    Role,
    EntryType,
    ToolCall,
    TranscriptEntry,
    Session,
    MemoryEntry,
)
from context.session_manager import SessionManager
from context.memory_system import MemorySystem
from context.context_manager import ContextManager, ContextConfig
from context.legacy_adapter import LegacySessionManagerAdapter

__all__ = [
    # 数据类
    "GroupType",
    "SessionStatus",
    "Role",
    "EntryType",
    "ToolCall",
    "TranscriptEntry",
    "Session",
    "MemoryEntry",
    # 核心类
    "SessionManager",
    "MemorySystem",
    "ContextManager",
    "ContextConfig",
    # 适配器
    "LegacySessionManagerAdapter",
]