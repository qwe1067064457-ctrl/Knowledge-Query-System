from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from retrieval_infra.contracts import ChunkDocument


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", text.lower())


class LexicalIndex:
    def __init__(self, db_path: Path, globals_path: Path) -> None:
        self.db_path = Path(db_path)
        self.globals_path = Path(globals_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.globals_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS postings (
                    term TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    tf INTEGER NOT NULL,
                    PRIMARY KEY (term, chunk_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS term_stats (
                    term TEXT PRIMARY KEY,
                    df INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunk_profiles (
                    chunk_id TEXT PRIMARY KEY,
                    doc_length INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        if not self.globals_path.exists():
            self.write_globals(total_docs=0, avg_doc_length=0.0)

    def rebuild(self, chunks: tuple[ChunkDocument, ...]) -> None:
        term_to_postings: dict[str, list[tuple[str, int]]] = defaultdict(list)
        term_df: Counter[str] = Counter()
        chunk_profiles: list[tuple[str, int]] = []
        total_terms = 0

        for chunk in chunks:
            terms = _tokenize(chunk.content)
            if not terms:
                continue
            frequencies = Counter(terms)
            chunk_profiles.append((chunk.chunk_id, len(terms)))
            total_terms += len(terms)
            for term, tf in frequencies.items():
                term_to_postings[term].append((chunk.chunk_id, tf))
                term_df[term] += 1

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM postings")
            conn.execute("DELETE FROM term_stats")
            conn.execute("DELETE FROM chunk_profiles")
            conn.executemany(
                "INSERT INTO postings(term, chunk_id, tf) VALUES (?, ?, ?)",
                [(term, chunk_id, tf) for term, postings in term_to_postings.items() for chunk_id, tf in postings],
            )
            conn.executemany(
                "INSERT INTO term_stats(term, df) VALUES (?, ?)",
                [(term, df) for term, df in term_df.items()],
            )
            conn.executemany(
                "INSERT INTO chunk_profiles(chunk_id, doc_length) VALUES (?, ?)",
                chunk_profiles,
            )
            conn.commit()

        total_docs = len(chunk_profiles)
        avg_doc_length = (total_terms / total_docs) if total_docs else 0.0
        self.write_globals(total_docs=total_docs, avg_doc_length=avg_doc_length)

    def write_globals(self, *, total_docs: int, avg_doc_length: float) -> None:
        self.globals_path.write_text(
            json.dumps({"total_docs": total_docs, "avg_doc_length": avg_doc_length}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_globals(self) -> dict[str, float]:
        return json.loads(self.globals_path.read_text(encoding="utf-8"))

    def query(self, text: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        query_terms = _tokenize(text)
        if not query_terms:
            return []
        globals_payload = self.load_globals()
        total_docs = int(globals_payload.get("total_docs", 0))
        avg_doc_length = float(globals_payload.get("avg_doc_length", 0.0) or 0.0)
        if total_docs <= 0 or avg_doc_length <= 0:
            return []

        with sqlite3.connect(self.db_path) as conn:
            chunk_lengths = {
                str(row[0]): int(row[1])
                for row in conn.execute("SELECT chunk_id, doc_length FROM chunk_profiles").fetchall()
            }
            term_stats = {
                str(row[0]): int(row[1])
                for row in conn.execute(
                    "SELECT term, df FROM term_stats WHERE term IN ({})".format(",".join("?" for _ in set(query_terms))),
                    tuple(set(query_terms)),
                ).fetchall()
            }
            scores: dict[str, float] = defaultdict(float)
            for term in query_terms:
                postings = conn.execute(
                    "SELECT chunk_id, tf FROM postings WHERE term = ?",
                    (term,),
                ).fetchall()
                if not postings:
                    continue
                df = term_stats.get(term, 0)
                idf = math.log(1 + ((total_docs - df + 0.5) / (df + 0.5))) if df else 0.0
                for chunk_id, tf in postings:
                    chunk_id = str(chunk_id)
                    doc_length = chunk_lengths.get(chunk_id, 0)
                    if doc_length <= 0:
                        continue
                    numerator = tf * (1.2 + 1.0)
                    denominator = tf + 1.2 * (1 - 0.75 + 0.75 * (doc_length / avg_doc_length))
                    scores[chunk_id] += idf * (numerator / denominator)

        return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
