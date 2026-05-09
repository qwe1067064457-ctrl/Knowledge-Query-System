"""
兼容适配器 - 将新的多领域 SessionManager 适配到旧的接口
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from context.session_manager import SessionManager as NewSessionManager
from context.dataclasses import TranscriptEntry, ToolCall


# 默认领域和 Agent
DEFAULT_GROUP = "general"
DEFAULT_AGENT = "default"


class LegacySessionManagerAdapter:
    """
    包装新的 SessionManager 以提供向后兼容的接口

    将旧格式（单 JSON 文件）映射到新格式（多领域 JSONL + SQLite）
    """

    def __init__(self, new_session_manager: NewSessionManager) -> None:
        self._inner = new_session_manager
        # 为了向后兼容，也使用旧的文件路径
        self._legacy_sessions_dir: Optional[Path] = None
        self._legacy_archive_dir: Optional[Path] = None

    def configure_legacy_paths(self, base_dir: Path) -> None:
        """配置旧版文件路径（用于向后兼容）"""
        self._legacy_sessions_dir = base_dir / "sessions"
        self._legacy_archive_dir = self._legacy_sessions_dir / "archive"
        self._legacy_sessions_dir.mkdir(parents=True, exist_ok=True)
        self._legacy_archive_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        if self._legacy_sessions_dir is None:
            raise RuntimeError("Legacy paths not configured")
        return self._legacy_sessions_dir / f"{session_id}.json"

    def _default_record(self, session_id: str, title: str = "新会话") -> dict[str, Any]:
        now = time.time()
        return {
            "id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "compressed_context": "",
            "messages": [],
        }

    @staticmethod
    def _estimate_tokens(content: str) -> int:
        return max(1, len(content or "") // 4) if content else 0

    @staticmethod
    def _normalize_tool_calls(
        tool_calls: list[dict[str, Any]] | None,
    ) -> list[ToolCall] | None:
        if not tool_calls:
            return None

        normalized: list[ToolCall] = []
        for index, tool_call in enumerate(tool_calls):
            call_id = str(
                tool_call.get("id")
                or tool_call.get("tool_call_id")
                or f"tool_{index}_{uuid.uuid4().hex[:8]}"
            )
            if isinstance(tool_call.get("function"), dict):
                function = tool_call["function"]
            else:
                function = {
                    "name": str(tool_call.get("tool") or tool_call.get("name") or "tool"),
                    "arguments": str(tool_call.get("input") or ""),
                }
            normalized.append(ToolCall(id=call_id, function=function))

        return normalized

    def _read_legacy_session(self, session_id: str) -> dict[str, Any]:
        """读取旧格式的会话文件"""
        if self._legacy_sessions_dir is None:
            # 如果没有配置旧路径，从新格式迁移过来
            return self._load_from_new_format(session_id)

        path = self._session_path(session_id)
        if not path.exists():
            # 尝试从新格式加载
            return self._load_from_new_format(session_id)

        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            record = self._default_record(session_id)
            record["messages"] = raw
            return record

        raw.setdefault("id", session_id)
        raw.setdefault("title", "新会话")
        raw.setdefault("created_at", time.time())
        raw.setdefault("updated_at", raw["created_at"])
        raw.setdefault("compressed_context", "")
        raw.setdefault("messages", [])
        return raw

    def _load_from_new_format(self, session_id: str) -> dict[str, Any]:
        """从新格式加载并转换为旧格式"""
        entries = self._inner.get_transcript(
            DEFAULT_GROUP, DEFAULT_AGENT, session_id,
            include_compacted=True
        )
        if not entries:
            return self._default_record(session_id)

        # 查找会话元数据
        session = self._inner.get_session(session_id, DEFAULT_GROUP, DEFAULT_AGENT)
        if session:
            created_at = session.created_at.timestamp()
            updated_at = session.last_active_at.timestamp()
        else:
            created_at = entries[0].timestamp / 1000
            updated_at = entries[-1].timestamp / 1000

        messages = []
        compressed_context = ""
        latest_compaction_index: int | None = None
        for index, entry in enumerate(entries):
            if entry.entry_type == "compaction" and entry.content:
                latest_compaction_index = index
                compressed_context = entry.content

        if latest_compaction_index is not None:
            entries = entries[latest_compaction_index + 1:]

        for entry in entries:
            if entry.entry_type == "compaction":
                # 压缩条目作为 compressed_context
                continue
            msg: dict[str, Any] = {"role": entry.role, "content": entry.content or ""}
            if entry.tool_calls:
                msg["tool_calls"] = [
                    {"id": tc.id, "function": tc.function}
                    for tc in entry.tool_calls
                ]
            messages.append(msg)

        return {
            "id": session_id,
            "title": f"会话 {session_id[:8]}",
            "created_at": created_at,
            "updated_at": updated_at,
            "compressed_context": compressed_context,
            "messages": messages,
        }

    def _write_legacy_session(self, record: dict[str, Any]) -> None:
        """写入旧格式的会话文件"""
        if self._legacy_sessions_dir is None:
            return
        session_id = str(record["id"])
        record["updated_at"] = time.time()
        self._session_path(session_id).write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def create_session(self, title: str = "新会话") -> dict[str, Any]:
        """创建新会话"""
        session = self._inner.create_session(
            DEFAULT_GROUP,
            DEFAULT_AGENT,
            "default",
            metadata={"title": title},
        )
        record = self._default_record(session.id, title=title)
        record["created_at"] = session.created_at.timestamp()
        record["updated_at"] = session.last_active_at.timestamp()
        self._write_legacy_session(record)
        return record

    def list_sessions(self) -> list[dict[str, Any]]:
        """列出所有会话"""
        records: list[dict[str, Any]] = []

        # 从新格式获取
        sessions = self._inner.list_user_sessions(
            DEFAULT_GROUP, DEFAULT_AGENT, "default",
            limit=100
        )

        for session in sessions:
            legacy_record = None
            if self._legacy_sessions_dir:
                legacy_path = self._session_path(session.id)
                if legacy_path.exists():
                    try:
                        legacy_record = json.loads(legacy_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        legacy_record = None

            title = (
                session.metadata.get("title")
                if session.metadata and session.metadata.get("title")
                else (legacy_record or {}).get("title", f"会话 {session.id[:8]}")
            )
            message_count = (
                len((legacy_record or {}).get("messages", []))
                if legacy_record
                else session.turn_count
            )
            records.append({
                "id": session.id,
                "title": title,
                "created_at": session.created_at.timestamp() * 1000,
                "updated_at": session.last_active_at.timestamp() * 1000,
                "message_count": message_count,
            })

        # 如果有旧格式的文件，也合并进来
        if self._legacy_sessions_dir:
            for path in self._legacy_sessions_dir.glob("*.json"):
                if path.parent == self._legacy_archive_dir:
                    continue
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                    session_id = record.get("id", path.stem)
                    # 跳过已经在新格式中的
                    if any(r["id"] == session_id for r in records):
                        continue
                    records.append({
                        "id": session_id,
                        "title": record.get("title", "新会话"),
                        "created_at": record.get("created_at"),
                        "updated_at": record.get("updated_at"),
                        "message_count": len(record.get("messages", [])),
                    })
                except json.JSONDecodeError:
                    continue

        return sorted(records, key=lambda item: item.get("updated_at") or 0, reverse=True)

    def load_session_record(self, session_id: str) -> dict[str, Any]:
        """加载会话完整记录"""
        return self._read_legacy_session(session_id)

    def load_session(self, session_id: str) -> list[dict[str, Any]]:
        """加载会话消息列表"""
        return self._read_legacy_session(session_id)["messages"]

    def load_session_for_agent(self, session_id: str) -> list[dict[str, str]]:
        """加载供 Agent 使用的消息列表（含压缩上下文）"""
        record = self._read_legacy_session(session_id)
        merged: list[dict[str, str]] = []

        compressed_context = record.get("compressed_context", "").strip()
        if compressed_context:
            merged.append({
                "role": "assistant",
                "content": f"[以下是之前对话的摘要]\n{compressed_context}",
            })

        for message in record.get("messages", []):
            role = message.get("role", "")
            content = str(message.get("content", "") or "")
            if role == "assistant" and merged and merged[-1]["role"] == "assistant":
                if content:
                    if merged[-1]["content"]:
                        merged[-1]["content"] += "\n\n" + content
                    else:
                        merged[-1]["content"] = content
                continue

            merged.append({"role": role, "content": content})

        return [item for item in merged if item["role"] in {"user", "assistant"}]

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        retrieval_steps: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """保存消息"""
        record = self._read_legacy_session(session_id)
        message: dict[str, Any] = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        if retrieval_steps:
            message["retrieval_steps"] = retrieval_steps
        record["messages"].append(message)
        self._write_legacy_session(record)

        # 同时写入新格式
        entry = TranscriptEntry(
            id=f"entry_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            group_id=DEFAULT_GROUP,
            timestamp=int(time.time() * 1000),
            role=role,
            entry_type="normal",
            content=content,
            tool_calls=self._normalize_tool_calls(tool_calls),
            token_count=self._estimate_tokens(content),
            metadata={"retrieval_steps": retrieval_steps} if retrieval_steps else None,
        )
        try:
            self._inner.append_entry(DEFAULT_GROUP, DEFAULT_AGENT, entry)
        except Exception:
            pass

        return message

    def get_history(self, session_id: str) -> dict[str, Any]:
        """获取会话历史"""
        return self._read_legacy_session(session_id)

    def rename_session(self, session_id: str, title: str) -> dict[str, Any]:
        """重命名会话"""
        record = self._read_legacy_session(session_id)
        record["title"] = title.strip() or "新会话"
        self._write_legacy_session(record)
        return record

    def set_title(self, session_id: str, title: str) -> dict[str, Any]:
        """设置会话标题"""
        return self.rename_session(session_id, title)

    def delete_session(self, session_id: str) -> None:
        """删除会话"""
        # 删除旧格式文件
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
        # 删除新格式
        try:
            self._inner.delete_session(session_id, DEFAULT_GROUP, DEFAULT_AGENT)
        except Exception:
            pass

    def compress_history(
        self,
        session_id: str,
        summary: str,
        n_messages: int
    ) -> dict[str, int]:
        """压缩会话历史"""
        record = self._read_legacy_session(session_id)
        messages = record.get("messages", [])
        archived = messages[:n_messages]
        remaining = messages[n_messages:]

        # 写入归档文件
        if self._legacy_archive_dir:
            archive_path = self._legacy_archive_dir / f"{session_id}_{int(time.time())}.json"
            archive_payload = {
                "session_id": session_id,
                "archived_at": time.time(),
                "messages": archived,
            }
            archive_path.write_text(
                json.dumps(archive_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # 更新压缩上下文
        existing_summary = record.get("compressed_context", "").strip()
        if existing_summary:
            record["compressed_context"] = f"{existing_summary}\n---\n{summary.strip()}"
        else:
            record["compressed_context"] = summary.strip()
        record["messages"] = remaining
        self._write_legacy_session(record)

        # 在新格式中也写入压缩条目
        compaction_entry = TranscriptEntry(
            id=f"compaction_{int(time.time() * 1000)}",
            session_id=session_id,
            group_id=DEFAULT_GROUP,
            timestamp=int(time.time() * 1000),
            role="system",
            entry_type="compaction",
            content=summary,
            token_count=self._estimate_tokens(summary),
        )
        try:
            self._inner.append_entry(DEFAULT_GROUP, DEFAULT_AGENT, compaction_entry)
        except Exception:
            pass

        return {
            "archived_count": len(archived),
            "remaining_count": len(remaining),
        }

    def get_compressed_context(self, session_id: str) -> str:
        """获取压缩上下文"""
        return self._read_legacy_session(session_id).get("compressed_context", "")
