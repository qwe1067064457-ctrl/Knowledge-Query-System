"""
context package exports.

Keep imports lazy to avoid circular dependencies between context and memory_system.
"""

from context.dataclasses import (
    EntryType,
    GroupType,
    MemoryEntry,
    MemoryScope,
    MemoryType,
    Role,
    Session,
    SessionStatus,
    ToolCall,
    TranscriptEntry,
)

__all__ = [
    "GroupType",
    "SessionStatus",
    "Role",
    "EntryType",
    "MemoryScope",
    "MemoryType",
    "ToolCall",
    "TranscriptEntry",
    "Session",
    "MemoryEntry",
    "SessionManager",
    "MemorySystem",
    "ContextManager",
    "ContextConfig",
    "LegacySessionManagerAdapter",
]


def __getattr__(name: str):
    if name == "SessionManager":
        from context.session_manager import SessionManager

        return SessionManager
    if name in {"ContextManager", "ContextConfig"}:
        from context.context_manager import ContextConfig, ContextManager

        return {"ContextManager": ContextManager, "ContextConfig": ContextConfig}[name]
    if name == "LegacySessionManagerAdapter":
        from context.legacy_adapter import LegacySessionManagerAdapter

        return LegacySessionManagerAdapter
    if name == "MemorySystem":
        from memory_system import MemorySystem

        return MemorySystem
    raise AttributeError(name)
