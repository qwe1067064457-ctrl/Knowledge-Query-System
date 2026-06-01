from __future__ import annotations

import sqlite3
from pathlib import Path


def _sqlite_path(path: Path) -> str:
    resolved = path.resolve()
    raw = str(resolved)
    if raw.startswith("\\\\?\\"):
        return raw
    if len(raw) >= 240 and resolved.drive:
        return f"\\\\?\\{raw}"
    return raw


class WorkQueue:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS build_queue (
                    build_id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_queue (
                    build_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (build_id, doc_id)
                )
                """
            )
            conn.commit()

    def enqueue_build(self, *, build_id: str, namespace: str, group_id: str, user_id: str | None, mode: str, status: str = "pending") -> None:
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO build_queue(build_id, namespace, group_id, user_id, mode, status) VALUES (?, ?, ?, ?, ?, ?)",
                (build_id, namespace, group_id, user_id, mode, status),
            )
            conn.commit()

    def enqueue_document(self, *, build_id: str, doc_id: str, source_path: str, stage: str, status: str = "pending") -> None:
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO document_queue(build_id, doc_id, source_path, stage, status) VALUES (?, ?, ?, ?, ?)",
                (build_id, doc_id, source_path, stage, status),
            )
            conn.commit()
