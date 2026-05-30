from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from retrieval_infra.contracts import ChunkDocument


class ChunkStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT,
                    namespace TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    locator_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    revision TEXT
                )
                """
            )
            conn.commit()

    def upsert_chunks(self, chunks: tuple[ChunkDocument, ...]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO chunks (
                    chunk_id, doc_id, group_id, user_id, namespace, source_kind, source_path,
                    file_type, content, locator_json, metadata_json, revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.doc_id,
                        chunk.group_id,
                        chunk.user_id,
                        chunk.namespace,
                        chunk.source_kind,
                        chunk.source_path,
                        chunk.file_type,
                        chunk.content,
                        json.dumps(chunk.locator, ensure_ascii=False),
                        json.dumps(chunk.metadata, ensure_ascii=False),
                        chunk.revision,
                    )
                    for chunk in chunks
                ],
            )
            conn.commit()

    def get_chunk_content(self, chunk_id: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT content FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        return None if row is None else str(row[0])
