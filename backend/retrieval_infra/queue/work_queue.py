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
    def __init__(self, db_path: Path, *, item_label: str = "document") -> None:
        if item_label not in {"document", "entry"}:
            raise ValueError("item_label must be 'document' or 'entry'")
        self.db_path = Path(db_path)
        self.item_label = item_label
        self.item_table = f"{item_label}_queue"
        self.item_id_column = "doc_id" if item_label == "document" else "entry_id"
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
                f"""
                CREATE TABLE IF NOT EXISTS {self.item_table} (
                    build_id TEXT NOT NULL,
                    {self.item_id_column} TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (build_id, {self.item_id_column})
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
        self._enqueue_item(build_id=build_id, item_id=doc_id, source_path=source_path, stage=stage, status=status)

    def enqueue_entry(self, *, build_id: str, entry_id: str, source_path: str, stage: str, status: str = "pending") -> None:
        self._enqueue_item(build_id=build_id, item_id=entry_id, source_path=source_path, stage=stage, status=status)

    def _enqueue_item(self, *, build_id: str, item_id: str, source_path: str, stage: str, status: str) -> None:
        with sqlite3.connect(_sqlite_path(self.db_path)) as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {self.item_table}(build_id, {self.item_id_column}, source_path, stage, status) VALUES (?, ?, ?, ?, ?)",
                (build_id, item_id, source_path, stage, status),
            )
            conn.commit()
