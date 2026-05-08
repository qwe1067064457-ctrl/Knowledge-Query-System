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

from context.dataclasses import Session, SessionStatus, TranscriptEntry


class SessionManager:
    """
    会话管理器

    支持多领域（legal/medical/general）数据隔离
    """

    def __init__(self, base_storage_path: Path) -> None:
        self.base_storage_path = Path(base_storage_path)
        self.groups_path = self.base_storage_path / "groups"
        self.groups_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_segment(value: str, field_name: str) -> str:
        """校验路径段，避免 group_id/agent_id 越界写入。"""
        if not value or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
            raise ValueError(
                f"{field_name} must only contain letters, numbers, dot, dash or underscore"
            )
        return value

    def _get_group_path(self, group_id: str, agent_id: str) -> Path:
        """获取指定组的会话存储路径"""
        group_id = self._safe_segment(group_id, "group_id")
        agent_id = self._safe_segment(agent_id, "agent_id")
        group_path = self.groups_path / group_id / "agents" / agent_id / "sessions"
        group_path.mkdir(parents=True, exist_ok=True)
        return group_path

    def _get_meta_path(self, group_id: str, agent_id: str, session_id: str) -> Path:
        return self._get_group_path(group_id, agent_id) / f"{session_id}.meta.json"

    def _load_meta(self, group_id: str, agent_id: str, session_id: str) -> Dict[str, Any]:
        meta_path = self._get_meta_path(group_id, agent_id, session_id)
        if not meta_path.exists():
            return {}
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_meta(self, group_id: str, agent_id: str, session: Session) -> None:
        meta_path = self._get_meta_path(group_id, agent_id, session.id)
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

    def _get_db_connection(self, group_id: str, agent_id: str) -> sqlite3.Connection:
        """获取指定组的数据库连接"""
        sessions_dir = self._get_group_path(group_id, agent_id)
        db_path = sessions_dir / "index.db"

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

        # 写入元数据
        sessions_dir = self._get_group_path(group_id, agent_id)
        self._write_meta(group_id, agent_id, session)

        # 创建空的 JSONL 文件
        transcript_path = sessions_dir / f"{session_id}.jsonl"
        transcript_path.touch()

        # 写入数据库索引
        conn = self._get_db_connection(group_id, agent_id)
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
        conn = self._get_db_connection(group_id, agent_id)
        cursor = conn.execute(
            """SELECT id, group_id, user_id, agent_id, created_at, last_active_at,
                      archived_at, status, turn_count, total_tokens
               FROM sessions WHERE id = ?""",
            (session_id,)
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

    def append_entry(
        self,
        group_id: str,
        agent_id: str,
        entry: TranscriptEntry
    ) -> None:
        """追加转录条目"""
        if entry.group_id != group_id:
            raise ValueError("entry.group_id must match group_id")

        sessions_dir = self._get_group_path(group_id, agent_id)
        transcript_path = sessions_dir / f"{entry.session_id}.jsonl"

        with open(transcript_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

        # 更新会话统计
        conn = self._get_db_connection(group_id, agent_id)

        # 检查会话是否存在于 SQLite 中
        cursor = conn.execute("SELECT id FROM sessions WHERE id = ?", (entry.session_id,))
        exists = cursor.fetchone() is not None

        if not exists:
            # 会话不存在，先创建一条记录（可能是旧格式迁移过来的会话）
            conn.execute(
                """INSERT OR IGNORE INTO sessions
                   (id, group_id, user_id, agent_id, created_at, last_active_at,
                    archived_at, status, turn_count, total_tokens)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.session_id,
                    group_id,
                    "default",  # user_id
                    agent_id,
                    entry.timestamp,  # created_at
                    entry.timestamp,  # last_active_at
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
                    user_id="default",
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
        sessions_dir = self._get_group_path(group_id, agent_id)
        transcript_path = sessions_dir / f"{session_id}.jsonl"

        if not transcript_path.exists():
            return []

        entries = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line.strip())

                # 过滤压缩条目
                if not include_compacted and data.get("entry_type") == "compaction":
                    continue

                # 时间过滤
                if since_timestamp and data.get("timestamp", 0) < since_timestamp:
                    continue

                # 从指定 ID 开始
                if from_id and data["id"] == from_id:
                    from_id = None
                if from_id:
                    continue

                entry = TranscriptEntry.from_dict(data)
                entries.append(entry)

                if limit and len(entries) >= limit:
                    break

        return entries

    def list_user_sessions(
        self,
        group_id: str,
        agent_id: str,
        user_id: str,
        status: Optional[SessionStatus] = None,
        limit: int = 20
    ) -> List[Session]:
        """列出用户的所有会话"""
        conn = self._get_db_connection(group_id, agent_id)

        query = """SELECT id, group_id, user_id, agent_id, created_at, last_active_at,
                          archived_at, status, turn_count, total_tokens
                   FROM sessions WHERE user_id = ?"""
        params: List[Any] = [user_id]

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
        conn = self._get_db_connection(group_id, agent_id)
        conn.execute(
            """UPDATE sessions
               SET status = ?, archived_at = ?
               WHERE id = ?""",
            (
                SessionStatus.ARCHIVED.value,
                int(datetime.now().timestamp() * 1000),
                session_id
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
        sessions_dir = self._get_group_path(group_id, agent_id)

        # 删除文件
        (sessions_dir / f"{session_id}.jsonl").unlink(missing_ok=True)
        (sessions_dir / f"{session_id}.meta.json").unlink(missing_ok=True)

        # 删除数据库记录
        conn = self._get_db_connection(group_id, agent_id)
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()

    def close(self) -> None:
        """关闭所有连接（需要时调用）"""
        pass  # 连接按需创建，无需集中关闭
