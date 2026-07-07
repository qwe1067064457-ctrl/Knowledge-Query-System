"""
会话管理器 - 多领域隔离的会话管理（JSONL + SQLite）
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from context.models import Session, SessionDialogueState, SessionStatus, TranscriptEntry
from context.session.session_working_memory import SessionWorkingMemory
from memory_system.session_working_memory.store import SessionWorkingMemoryStore


DEFAULT_GROUP = "general"
DEFAULT_AGENT = "default"
DEFAULT_USER = "default"
_DIALOGUE_STATE_KEY = "dialogue_state"
_WORKING_MEMORY_KEY = "session_working_memory"


class SessionManager:
    """
    会话管理器

    支持多领域（legal/medical/general）数据隔离
    """

    def __init__(self, base_storage_path: Path) -> None:
        self.base_storage_path = Path(base_storage_path)
        self.groups_path = self.base_storage_path / "groups"
        self.groups_path.mkdir(parents=True, exist_ok=True)
        self.working_memory_store = SessionWorkingMemoryStore(self.base_storage_path)

    @staticmethod
    def _safe_segment(value: str, field_name: str) -> str:
        """校验路径段，避免 group_id/agent_id 越界写入。"""
        if not value or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
            raise ValueError(
                f"{field_name} must only contain letters, numbers, dot, dash or underscore"
            )
        return value

    def _get_group_root(self, group_id: str) -> Path:
        group_id = self._safe_segment(group_id, "group_id")
        group_path = self.groups_path / group_id
        group_path.mkdir(parents=True, exist_ok=True)
        return group_path

    def _get_user_sessions_path(self, group_id: str, user_id: str) -> Path:
        user_id = self._safe_segment(user_id, "user_id")
        sessions_path = self._get_group_root(group_id) / "users" / user_id / "sessions"
        (sessions_path / "transcripts").mkdir(parents=True, exist_ok=True)
        (sessions_path / "agent_traces").mkdir(parents=True, exist_ok=True)
        return sessions_path

    def _get_meta_path(self, group_id: str, user_id: str, session_id: str) -> Path:
        return self._get_user_sessions_path(group_id, user_id) / f"{session_id}.meta.json"

    def _get_transcript_path(self, group_id: str, user_id: str, session_id: str) -> Path:
        return self._get_user_sessions_path(group_id, user_id) / "transcripts" / f"{session_id}.jsonl"

    def _get_agent_trace_path(self, group_id: str, user_id: str, session_id: str) -> Path:
        return self._get_user_sessions_path(group_id, user_id) / "agent_traces" / f"{session_id}.jsonl"

    def _resolve_user_id(self, group_id: str, session_id: str, agent_id: str) -> Optional[str]:
        self._safe_segment(agent_id, "agent_id")
        conn = self._get_db_connection(group_id)
        try:
            cursor = conn.execute(
                "SELECT user_id FROM sessions WHERE id = ? AND agent_id = ?",
                (session_id, agent_id),
            )
            row = cursor.fetchone()
        finally:
            conn.close()
        if row:
            return str(row[0])
        return None

    def resolve_user_id_any_group(self, session_id: str, agent_id: str) -> Optional[str]:
        self._safe_segment(agent_id, "agent_id")
        if not self.groups_path.exists():
            return None
        for group_dir in sorted(path for path in self.groups_path.iterdir() if path.is_dir()):
            conn = self._get_db_connection(group_dir.name)
            try:
                cursor = conn.execute(
                    "SELECT user_id FROM sessions WHERE id = ? AND agent_id = ?",
                    (session_id, agent_id),
                )
                row = cursor.fetchone()
            finally:
                conn.close()
            if row:
                return str(row[0])
        return None

    def _load_meta(self, group_id: str, agent_id: str, session_id: str) -> Dict[str, Any]:
        user_id = self._resolve_user_id(group_id, session_id, agent_id)
        if user_id:
            meta_path = self._get_meta_path(group_id, user_id, session_id)
            if meta_path.exists():
                try:
                    return json.loads(meta_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    return {}
        return {}

    def _write_meta(self, group_id: str, agent_id: str, session: Session) -> None:
        del agent_id
        meta_path = self._get_meta_path(group_id, session.user_id, session.id)
        meta_path.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_active_at INTEGER NOT NULL,
                archived_at INTEGER,
                status TEXT NOT NULL,
                turn_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_status_activity
            ON sessions (user_id, status, last_active_at DESC)
        """)
        conn.commit()

    def _get_db_connection(self, group_id: str) -> sqlite3.Connection:
        """获取指定组的数据库连接。"""
        db_path = self._get_group_root(group_id) / "session_index.sqlite"
        conn = sqlite3.connect(str(db_path))
        self._ensure_schema(conn)
        return conn

    def create_session(
        self,
        group_id: str,
        agent_id: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Session:
        """创建新会话"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        user_id = self._safe_segment(user_id, "user_id")
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        now = datetime.now()

        session = Session(
            id=session_id,
            group_id=group_id,
            user_id=user_id,
            agent_id=agent_id,
            created_at=now,
            last_active_at=now,
            status=SessionStatus.ACTIVE,
            metadata=metadata
        )

        self._write_meta(group_id, agent_id, session)
        transcript_path = self._get_transcript_path(group_id, user_id, session_id)
        transcript_path.touch()
        self._get_agent_trace_path(group_id, user_id, session_id).touch()

        conn = self._get_db_connection(group_id)
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                group_id,
                user_id,
                agent_id,
                int(now.timestamp() * 1000),
                int(now.timestamp() * 1000),
                None,
                SessionStatus.ACTIVE.value,
                0,
                0
            )
        )
        conn.commit()
        conn.close()

        return session

    def get_session(
        self,
        session_id: str,
        group_id: str,
        agent_id: str
    ) -> Optional[Session]:
        """获取会话元数据"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        conn = self._get_db_connection(group_id)
        cursor = conn.execute(
            """SELECT id, group_id, user_id, agent_id, created_at, last_active_at,
                      archived_at, status, turn_count, total_tokens
               FROM sessions WHERE id = ? AND agent_id = ?""",
            (session_id, agent_id)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        meta = self._load_meta(group_id, agent_id, session_id)

        return Session(
            id=row[0],
            group_id=row[1],
            user_id=row[2],
            agent_id=row[3],
            created_at=datetime.fromtimestamp(row[4] / 1000),
            last_active_at=datetime.fromtimestamp(row[5] / 1000),
            archived_at=datetime.fromtimestamp(row[6] / 1000) if row[6] else None,
            status=SessionStatus(row[7]),
            turn_count=row[8],
            total_tokens=row[9],
            metadata=meta.get("metadata"),
        )

    def update_session_metadata(
        self,
        session_id: str,
        group_id: str,
        agent_id: str,
        metadata: Dict[str, Any],
    ) -> Optional[Session]:
        agent_id = self._safe_segment(agent_id, "agent_id")
        session = self.get_session(session_id, group_id, agent_id)
        if session is None:
            return None
        session.metadata = metadata
        self._write_meta(group_id, agent_id, session)
        return session

    def get_dialogue_state(
        self,
        session_id: str,
        group_id: str,
        agent_id: str,
    ) -> SessionDialogueState | None:
        agent_id = self._safe_segment(agent_id, "agent_id")
        session = self.get_session(session_id, group_id, agent_id)
        if session is None:
            return None
        metadata = session.metadata or {}
        payload = metadata.get(_DIALOGUE_STATE_KEY)
        if not isinstance(payload, dict):
            return None
        return SessionDialogueState.from_dict(payload)

    def update_dialogue_state(
        self,
        session_id: str,
        group_id: str,
        agent_id: str,
        state: SessionDialogueState | dict[str, Any],
    ) -> Optional[Session]:
        agent_id = self._safe_segment(agent_id, "agent_id")
        session = self.get_session(session_id, group_id, agent_id)
        if session is None:
            return None
        state_payload = (
            state.to_dict()
            if isinstance(state, SessionDialogueState)
            else SessionDialogueState.from_dict(state).to_dict()
        )
        metadata = dict(session.metadata or {})
        metadata[_DIALOGUE_STATE_KEY] = state_payload
        session.metadata = metadata
        self._write_meta(group_id, agent_id, session)
        return session

    def get_working_memory(
        self,
        session_id: str,
        group_id: str,
        agent_id: str,
    ) -> SessionWorkingMemory | None:
        agent_id = self._safe_segment(agent_id, "agent_id")
        session = self.get_session(session_id, group_id, agent_id)
        if session is None:
            return None
        loaded = self.working_memory_store.load(
            group_id=group_id,
            agent_id=agent_id,
            session_id=session_id,
            user_id=session.user_id,
        )
        if loaded is not None:
            return loaded
        metadata = session.metadata or {}
        payload = metadata.get(_WORKING_MEMORY_KEY)
        if not isinstance(payload, dict):
            return None
        migrated = SessionWorkingMemory.from_dict(payload)
        self.working_memory_store.save(
            group_id=group_id,
            agent_id=agent_id,
            session_id=session_id,
            memory=migrated,
        )
        return migrated

    def update_working_memory(
        self,
        session_id: str,
        group_id: str,
        agent_id: str,
        memory: SessionWorkingMemory | dict[str, Any],
    ) -> Optional[Session]:
        agent_id = self._safe_segment(agent_id, "agent_id")
        session = self.get_session(session_id, group_id, agent_id)
        if session is None:
            return None
        normalized = self.working_memory_store.save(
            group_id=group_id,
            agent_id=agent_id,
            session_id=session_id,
            user_id=session.user_id,
            memory=memory,
        )
        metadata = dict(session.metadata or {})
        metadata[_WORKING_MEMORY_KEY] = normalized.to_dict()
        session.metadata = metadata
        self._write_meta(group_id, agent_id, session)
        return session

    def append_entry(
        self,
        group_id: str,
        agent_id: str,
        entry: TranscriptEntry
    ) -> None:
        """追加转录条目"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        if entry.group_id != group_id:
            raise ValueError("entry.group_id must match group_id")

        user_id = self._resolve_user_id(group_id, entry.session_id, agent_id) or DEFAULT_USER
        transcript_path = self._get_transcript_path(group_id, user_id, entry.session_id)

        with open(transcript_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

        conn = self._get_db_connection(group_id)
        cursor = conn.execute("SELECT id FROM sessions WHERE id = ? AND agent_id = ?", (entry.session_id, agent_id))
        exists = cursor.fetchone() is not None

        if not exists:
            conn.execute(
                """INSERT OR IGNORE INTO sessions
                   (id, group_id, user_id, agent_id, created_at, last_active_at,
                    archived_at, status, turn_count, total_tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.session_id,
                    group_id,
                    user_id,
                    agent_id,
                    entry.timestamp,
                    entry.timestamp,
                    None,
                    SessionStatus.ACTIVE.value,
                    1 if entry.role == "user" else 0,
                    entry.token_count or 0
                )
            )
            self._write_meta(
                group_id,
                agent_id,
                Session(
                    id=entry.session_id,
                    group_id=group_id,
                    user_id=user_id,
                    agent_id=agent_id,
                    created_at=datetime.fromtimestamp(entry.timestamp / 1000),
                    last_active_at=datetime.fromtimestamp(entry.timestamp / 1000),
                    status=SessionStatus.ACTIVE,
                    turn_count=1 if entry.role == "user" else 0,
                    total_tokens=entry.token_count or 0,
                ),
            )
        elif entry.role == "user":
            conn.execute(
                """UPDATE sessions
                   SET turn_count = turn_count + 1,
                       last_active_at = ?,
                       total_tokens = total_tokens + ?
                   WHERE id = ?""",
                (entry.timestamp, entry.token_count or 0, entry.session_id)
            )
        else:
            conn.execute(
                """UPDATE sessions
                   SET last_active_at = ?,
                       total_tokens = total_tokens + ?
                   WHERE id = ?""",
                (entry.timestamp, entry.token_count or 0, entry.session_id)
            )
        conn.commit()
        conn.close()

        session = self.get_session(entry.session_id, group_id, agent_id)
        if session:
            self._write_meta(group_id, agent_id, session)

    def get_transcript(
        self,
        group_id: str,
        agent_id: str,
        session_id: str,
        limit: Optional[int] = None,
        from_id: Optional[str] = None,
        include_compacted: bool = True,
        since_timestamp: Optional[int] = None
    ) -> List[TranscriptEntry]:
        """获取会话转录"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        user_id = self._resolve_user_id(group_id, session_id, agent_id)
        if not user_id:
            return []
        transcript_path = self._get_transcript_path(group_id, user_id, session_id)
        if not transcript_path.exists():
            return []

        entries = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line.strip())

                if not include_compacted and data.get("entry_type") == "compaction":
                    continue
                if since_timestamp and data.get("timestamp", 0) < since_timestamp:
                    continue
                if from_id and data["id"] == from_id:
                    from_id = None
                if from_id:
                    continue

                entry = TranscriptEntry.from_dict(data)
                entries.append(entry)
                if limit and len(entries) >= limit:
                    break

        return entries

    def append_agent_trace(
        self,
        group_id: str,
        agent_id: str,
        session_id: str,
        trace_record: Dict[str, Any],
    ) -> None:
        """将 agent 决策链路独立写入与 transcript 隔离的 trace 文件。"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        user_id = self._resolve_user_id(group_id, session_id, agent_id)
        if not user_id:
            raise ValueError("session not found for trace persistence")
        trace_path = self._get_agent_trace_path(group_id, user_id, session_id)
        with open(trace_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(trace_record, ensure_ascii=False) + "\n")

    def get_agent_traces(
        self,
        group_id: str,
        agent_id: str,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """读取与 transcript 隔离的 agent trace 历史。"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        user_id = self._resolve_user_id(group_id, session_id, agent_id)
        if not user_id:
            return []
        trace_path = self._get_agent_trace_path(group_id, user_id, session_id)
        if not trace_path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        with open(trace_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
        return rows

    def list_user_sessions(
        self,
        group_id: str,
        agent_id: str,
        user_id: str,
        status: Optional[SessionStatus] = None,
        limit: int = 20
    ) -> List[Session]:
        """列出用户的所有会话"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        conn = self._get_db_connection(group_id)

        query = """SELECT id, group_id, user_id, agent_id, created_at, last_active_at,
                          archived_at, status, turn_count, total_tokens
                   FROM sessions WHERE user_id = ? AND agent_id = ?"""
        params: List[Any] = [user_id, agent_id]

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY last_active_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        sessions = []
        for row in cursor.fetchall():
            meta = self._load_meta(group_id, agent_id, row[0])
            sessions.append(Session(
                id=row[0],
                group_id=row[1],
                user_id=row[2],
                agent_id=row[3],
                created_at=datetime.fromtimestamp(row[4] / 1000),
                last_active_at=datetime.fromtimestamp(row[5] / 1000),
                archived_at=datetime.fromtimestamp(row[6] / 1000) if row[6] else None,
                status=SessionStatus(row[7]),
                turn_count=row[8],
                total_tokens=row[9],
                metadata=meta.get("metadata"),
            ))

        conn.close()
        return sessions

    def archive_session(
        self,
        session_id: str,
        group_id: str,
        agent_id: str
    ) -> None:
        """归档会话"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        conn = self._get_db_connection(group_id)
        conn.execute(
            """UPDATE sessions
               SET status = ?, archived_at = ?
               WHERE id = ? AND agent_id = ?""",
            (
                SessionStatus.ARCHIVED.value,
                int(datetime.now().timestamp() * 1000),
                session_id,
                agent_id,
            )
        )
        conn.commit()
        conn.close()

        session = self.get_session(session_id, group_id, agent_id)
        if session:
            self._write_meta(group_id, agent_id, session)

    def delete_session(
        self,
        session_id: str,
        group_id: str,
        agent_id: str
    ) -> None:
        """删除会话"""
        agent_id = self._safe_segment(agent_id, "agent_id")
        user_id = self._resolve_user_id(group_id, session_id, agent_id)
        if user_id:
            self._get_transcript_path(group_id, user_id, session_id).unlink(missing_ok=True)
            self._get_agent_trace_path(group_id, user_id, session_id).unlink(missing_ok=True)
            self._get_meta_path(group_id, user_id, session_id).unlink(missing_ok=True)

        conn = self._get_db_connection(group_id)
        conn.execute("DELETE FROM sessions WHERE id = ? AND agent_id = ?", (session_id, agent_id))
        conn.commit()
        conn.close()

    def close(self) -> None:
        """关闭所有连接（需要时调用）"""
        pass
