from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from retrieval_infra.adapters import KnowledgeSourceAdapter
from retrieval_infra.chunking import TextChunker
from retrieval_infra.contracts import BuildCheckpoint, BuildRequest, IndexManifest
from retrieval_infra.indexing.chunk_store import ChunkStore
from retrieval_infra.indexing.lexical_index import LexicalIndex
from retrieval_infra.indexing.manifest_store import ManifestStore
from retrieval_infra.indexing.state_store import StateStore
from retrieval_infra.indexing.vector_index import SimpleVectorIndex
from retrieval_infra.normalization import DocumentNormalizer
from retrieval_infra.parsing import SimpleTextParser, SourceReader
from retrieval_infra.queue import WorkQueue

from knowledge_retrieval.types import IndexStatus


@dataclass(frozen=True)
class GroupKnowledgeAssets:
    chunk_store: ChunkStore
    lexical: LexicalIndex
    vector: SimpleVectorIndex
    chunk_meta: dict[str, dict[str, object]]


class RepoKnowledgeIndexManager:
    def __init__(self, backend_dir: Path | None = None) -> None:
        self.backend_dir = Path(backend_dir) if backend_dir is not None else Path(__file__).resolve().parents[2]
        self.storage_groups_dir = self.backend_dir / "storage" / "groups"
        self.knowledge_adapter = KnowledgeSourceAdapter()
        self.reader = SourceReader()
        self.parser = SimpleTextParser()
        self.normalizer = DocumentNormalizer()
        self.chunker = TextChunker()
        self._building = False
        self._last_built_at: float | None = None

    def configure(self, backend_dir: Path) -> None:
        self.backend_dir = Path(backend_dir)
        self.storage_groups_dir = self.backend_dir / "storage" / "groups"

    def is_building(self) -> bool:
        return self._building

    def status(self) -> IndexStatus:
        indexed_files = 0
        vector_ready = False
        bm25_ready = False
        for group_id in self._discover_groups():
            slot_dir = self._active_slot_dir(group_id)
            if (slot_dir / "chunk_store.sqlite").exists():
                indexed_files += 1
            if (slot_dir / "vector" / "index.sqlite").exists():
                vector_ready = True
            if (slot_dir / "lexical" / "term_postings.sqlite").exists():
                bm25_ready = True
        ready = indexed_files > 0 and (vector_ready or bm25_ready)
        return IndexStatus(
            ready=ready,
            building=self._building,
            last_built_at=self._last_built_at,
            indexed_files=indexed_files,
            vector_ready=vector_ready,
            bm25_ready=bm25_ready,
        )

    def rebuild_index(self) -> None:
        self._building = True
        try:
            for group_id in self._discover_groups():
                self._build_group(group_id, mode="full")
        finally:
            self._building = False

    def ensure_group_built(self, group_id: str) -> GroupKnowledgeAssets:
        slot_dir = self._active_slot_dir(group_id)
        manifest = self._manifest_store(group_id).load("knowledge")
        if not (slot_dir / "chunk_store.sqlite").exists():
            self._build_group(group_id, mode="full", preferred_target_slot="next" if manifest.active_slot == "current" else "current")
            slot_dir = self._active_slot_dir(group_id)
        return self._load_assets(slot_dir)

    def _build_group(self, group_id: str, *, mode: str, preferred_target_slot: str | None = None) -> None:
        manifest_store = self._manifest_store(group_id)
        manifest = manifest_store.load("knowledge")
        active_slot = manifest.active_slot
        target_slot = preferred_target_slot or ("next" if active_slot == "current" else "current")
        target_dir = self._slot_dir(group_id, target_slot)
        source_documents = tuple(self._load_group_sources(group_id))
        build_id = f"build_{group_id}_{target_slot}"
        request = BuildRequest(
            build_id=build_id,
            group_id=group_id,
            namespace="knowledge",
            mode=mode,  # type: ignore[arg-type]
            target_slot=target_slot,  # type: ignore[arg-type]
            source_ids=tuple(doc.source_id for doc in source_documents),
        )
        state_store = self._state_store(group_id)
        state_store.append_build(request, status="running")
        self._work_queue(group_id).enqueue_build(build_id=build_id, namespace="knowledge", group_id=group_id, user_id=None, mode=mode, status="running")

        chunks = []
        chunk_meta: dict[str, dict[str, object]] = {}
        scanned_count = 0
        last_seen_file = ""
        last_seen_hash = ""
        last_seen_mtime = 0
        for source in source_documents:
            scanned_count += 1
            last_seen_file = source.source_path
            if source.revision:
                parts = source.revision.split(":")
                if len(parts) == 2:
                    try:
                        last_seen_mtime = int(parts[0])
                    except ValueError:
                        last_seen_mtime = 0
                last_seen_hash = source.revision
            self._work_queue(group_id).enqueue_document(
                build_id=build_id,
                doc_id=self._doc_id_for_source(source.source_path),
                source_path=source.source_path,
                stage="parsing",
                status="running",
            )
            parsed = self.parser.parse(self._doc_id_for_source(source.source_path), source)
            normalized = self.normalizer.normalize(parsed)
            doc_chunks = self.chunker.chunk(normalized)
            for chunk in doc_chunks:
                chunks.append(chunk)
                chunk_meta[chunk.chunk_id] = {
                    "doc_id": chunk.doc_id,
                    "source_path": chunk.source_path,
                    "locator": chunk.locator,
                    "file_type": chunk.file_type,
                }
            state_store.write_checkpoint(
                BuildCheckpoint(
                    source_id=source.source_id,
                    build_id=build_id,
                    group_id=group_id,
                    namespace="knowledge",
                    user_id=None,
                    scan_checkpoint={
                        "mode": "file_tree",
                        "last_seen_file": last_seen_file,
                        "last_seen_mtime": last_seen_mtime,
                        "last_seen_hash": last_seen_hash,
                        "scanned_file_count": scanned_count,
                    },
                    doc_local_progress={"chunk_index": max(0, len(doc_chunks) - 1)},
                    pipeline_progress={
                        "stage": "chunked",
                        "parsed_docs": scanned_count,
                        "chunked_docs": scanned_count,
                        "embedded_chunks": len(chunks),
                        "indexed_lexical_chunks": 0,
                        "indexed_vector_chunks": 0,
                    },
                )
            )

        chunk_tuple = tuple(chunks)
        chunk_store = ChunkStore(target_dir / "chunk_store.sqlite")
        lexical = LexicalIndex(target_dir / "lexical" / "term_postings.sqlite", target_dir / "lexical" / "globals.json")
        vector = SimpleVectorIndex(target_dir / "vector" / "index.sqlite")
        chunk_store.upsert_chunks(chunk_tuple)
        lexical.rebuild(chunk_tuple)
        vector.rebuild(chunk_tuple)
        (target_dir / "chunk_meta.json").write_text(json.dumps(chunk_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        (target_dir / "build_fingerprint.json").write_text(
            json.dumps({"fingerprint": self._fingerprint_sources(source_documents)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        state_store.append_build(request, status="completed")
        snapshot_id = f"{group_id}_{target_slot}"
        self._snapshot_slot(group_id, target_slot, snapshot_id)
        manifest_store.switch("knowledge", active_slot=target_slot, previous_slot=active_slot, snapshot_id=snapshot_id)
        state_store.append_build(request, status="switched")
        self._last_built_at = self._current_timestamp()

    def _discover_groups(self) -> list[str]:
        groups = {path.name for path in self.storage_groups_dir.iterdir() if path.is_dir()} if self.storage_groups_dir.exists() else set()
        return sorted(groups)

    def _load_group_sources(self, group_id: str) -> Iterable:
        for root in self._group_source_roots(group_id):
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                content = self.reader.read_file_content(path)
                if not content.strip():
                    continue
                yield self.knowledge_adapter.build_source_document(
                    source_id=self._source_id_for_path(group_id, path),
                    group_id=group_id,
                    source_path=self._relative_source_path(path),
                    content=content,
                    file_type=path.suffix.lower().lstrip(".") or "text",
                    metadata={"title": path.stem},
                    revision=self._revision_for_path(path),
                )

    def _group_source_roots(self, group_id: str) -> Iterable[Path]:
        storage_raw = self.storage_groups_dir / group_id / "knowledge" / "raw"
        if storage_raw.exists():
            yield storage_raw

    def _manifest_store(self, group_id: str) -> ManifestStore:
        return ManifestStore(self.storage_groups_dir / group_id / "registries" / "index_manifest.json")

    def _state_store(self, group_id: str) -> StateStore:
        return StateStore(
            build_registry_path=self.storage_groups_dir / group_id / "registries" / "build_registry.jsonl",
            checkpoints_path=self.storage_groups_dir / group_id / "registries" / "checkpoints.json",
        )

    def _work_queue(self, group_id: str) -> WorkQueue:
        return WorkQueue(self.storage_groups_dir / group_id / "registries" / "work_queue.sqlite")

    def _slot_dir(self, group_id: str, slot: str) -> Path:
        path = self.storage_groups_dir / group_id / "knowledge" / "indexes" / slot
        (path / "lexical").mkdir(parents=True, exist_ok=True)
        (path / "vector").mkdir(parents=True, exist_ok=True)
        return path

    def _active_slot_dir(self, group_id: str) -> Path:
        manifest = self._manifest_store(group_id).load("knowledge")
        return self._slot_dir(group_id, manifest.active_slot)

    def _snapshot_slot(self, group_id: str, slot: str, snapshot_id: str) -> None:
        source_dir = self._slot_dir(group_id, slot)
        snapshot_dir = self.storage_groups_dir / group_id / "knowledge" / "indexes" / "snapshots" / snapshot_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        for relative in (
            Path("chunk_store.sqlite"),
            Path("chunk_meta.json"),
            Path("build_fingerprint.json"),
            Path("lexical") / "term_postings.sqlite",
            Path("lexical") / "globals.json",
            Path("vector") / "index.sqlite",
        ):
            source = source_dir / relative
            if not source.exists():
                continue
            target = snapshot_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (snapshot_dir / "manifest.json").write_text(
            json.dumps(IndexManifest(namespace="knowledge", active_slot=slot, previous_slot=None, snapshot_id=snapshot_id).to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_assets(self, slot_dir: Path) -> GroupKnowledgeAssets:
        chunk_meta_path = slot_dir / "chunk_meta.json"
        return GroupKnowledgeAssets(
            chunk_store=ChunkStore(slot_dir / "chunk_store.sqlite"),
            lexical=LexicalIndex(slot_dir / "lexical" / "term_postings.sqlite", slot_dir / "lexical" / "globals.json"),
            vector=SimpleVectorIndex(slot_dir / "vector" / "index.sqlite"),
            chunk_meta=json.loads(chunk_meta_path.read_text(encoding="utf-8")) if chunk_meta_path.exists() else {},
        )

    def _relative_source_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.backend_dir)).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    def _source_id_for_path(self, group_id: str, path: Path) -> str:
        relative = self._relative_source_path(path)
        return f"{group_id}:{hashlib.md5(relative.encode('utf-8')).hexdigest()}"

    def _doc_id_for_source(self, source_path: str) -> str:
        return f"doc_{hashlib.md5(source_path.encode('utf-8')).hexdigest()}"

    def _revision_for_path(self, path: Path) -> str:
        stat = path.stat()
        return f"{int(stat.st_mtime)}:{stat.st_size}"

    def _fingerprint_sources(self, sources: tuple) -> str:
        digest = hashlib.md5()
        for source in sources:
            digest.update(source.source_id.encode("utf-8"))
            digest.update((source.revision or "").encode("utf-8"))
        return digest.hexdigest()

    def _current_timestamp(self) -> float:
        import time
        return time.time()
