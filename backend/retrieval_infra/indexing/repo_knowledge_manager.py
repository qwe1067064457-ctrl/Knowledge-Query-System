from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Iterable
import uuid

from retrieval_infra.adapters import KnowledgeSourceAdapter
from retrieval_infra.chunking import TextChunker
from retrieval_infra.contracts import BuildRequest, IndexManifest
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
    text_lexical: LexicalIndex
    text_vector: SimpleVectorIndex
    table_lexical: LexicalIndex
    table_vector: SimpleVectorIndex
    chunk_meta: dict[str, dict[str, object]]

    @property
    def lexical(self) -> LexicalIndex:
        return self.text_lexical

    @property
    def vector(self) -> SimpleVectorIndex:
        return self.text_vector


@dataclass(frozen=True)
class DocumentBuildResult:
    source_id: str
    source_path: str
    doc_id: str
    doc_kind: str
    status: str
    doc_chunks: tuple
    text_chunk_count: int
    table_record_count: int
    warnings: tuple[str, ...]
    error: str | None = None


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
            current_dir = self._current_dir(group_id)
            if (current_dir / "chunk_store.sqlite").exists():
                indexed_files += 1
            if (current_dir / "text_pool" / "vector" / "index.sqlite").exists() or (current_dir / "table_pool" / "vector" / "index.sqlite").exists():
                vector_ready = True
            if (current_dir / "text_pool" / "lexical" / "term_postings.sqlite").exists() or (current_dir / "table_pool" / "lexical" / "term_postings.sqlite").exists():
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
        current_dir = self._current_dir(group_id)
        if not (current_dir / "chunk_store.sqlite").exists():
            self._build_group(group_id, mode="full")
        return self._load_assets(self._current_dir(group_id))

    def _build_group(self, group_id: str, *, mode: str) -> None:
        manifest_store = self._manifest_store(group_id)
        manifest = manifest_store.load("knowledge")
        source_documents = tuple(self._load_group_sources(group_id))
        source_fingerprint = self._fingerprint_sources(source_documents)
        build_id = self._new_build_id(group_id)
        candidate_dir = self._candidate_dir(group_id, build_id)
        candidate_dir.mkdir(parents=True, exist_ok=True)
        self._prepare_candidate_layout(candidate_dir)

        request = BuildRequest(
            build_id=build_id,
            group_id=group_id,
            namespace="knowledge",
            mode=mode,  # type: ignore[arg-type]
            source_ids=tuple(doc.source_id for doc in source_documents),
            source_fingerprint=source_fingerprint,
            candidate_dir=str(candidate_dir),
        )
        state_store = self._state_store(group_id)
        state_store.append_build(request, status="running")
        self._write_source_registry(group_id, request=request, source_documents=source_documents, state_store=state_store)
        self._work_queue(group_id).enqueue_build(
            build_id=build_id,
            namespace="knowledge",
            group_id=group_id,
            user_id=None,
            mode=mode,
            status="running",
        )

        all_chunks = []
        text_chunks = []
        table_chunks = []
        chunk_meta: dict[str, dict[str, object]] = {}
        doc_results: list[dict[str, object]] = []
        worker_count = self._document_worker_count(len(source_documents))
        for source in source_documents:
            doc_id = self._doc_id_for_source(source.source_path)
            doc_kind = self._doc_kind_for_source(source.file_type)
            self._work_queue(group_id).enqueue_document(
                build_id=build_id,
                doc_id=doc_id,
                source_path=source.source_path,
                stage="running",
                status="running",
            )
            state_store.write_document_checkpoint(
                build_id=build_id,
                doc_id=doc_id,
                source_id=source.source_id,
                source_path=source.source_path,
                    doc_kind=doc_kind,
                    stage="started",
                    status="running",
                )
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix=f"kb-{group_id}") as executor:
            future_map = {executor.submit(self._process_source_document, source): source for source in source_documents}
            for future in as_completed(future_map):
                source = future_map[future]
                result = future.result()
                doc_results.append(
                    {
                        "source_id": result.source_id,
                        "doc_id": result.doc_id,
                        "source_path": result.source_path,
                        "doc_kind": result.doc_kind,
                        "chunk_count": result.text_chunk_count,
                        "table_record_count": result.table_record_count,
                        "status": result.status,
                        "warnings": list(result.warnings),
                        "error": result.error,
                    }
                )
                if result.status != "completed":
                    state_store.write_document_checkpoint(
                        build_id=build_id,
                        doc_id=result.doc_id,
                        source_id=result.source_id,
                        source_path=result.source_path,
                        doc_kind=result.doc_kind,
                        stage="failed",
                        status="failed",
                        error=result.error or "document task failed",
                    )
                    self._work_queue(group_id).enqueue_document(
                        build_id=build_id,
                        doc_id=result.doc_id,
                        source_path=result.source_path,
                        stage="failed",
                        status="failed",
                    )
                    continue
                for chunk in result.doc_chunks:
                    all_chunks.append(chunk)
                    if bool(chunk.metadata.get("structured_only")):
                        table_chunks.append(chunk)
                        pool = "table"
                    else:
                        text_chunks.append(chunk)
                        pool = "text"
                    chunk_meta[chunk.chunk_id] = {
                        "doc_id": chunk.doc_id,
                        "source_path": chunk.source_path,
                        "locator": chunk.locator,
                        "file_type": chunk.file_type,
                        "pool": pool,
                        "structured_only": bool(chunk.metadata.get("structured_only")),
                        "analysis_available": bool(chunk.metadata.get("analysis_available", False)),
                    }
                state_store.write_document_checkpoint(
                    build_id=build_id,
                    doc_id=result.doc_id,
                    source_id=result.source_id,
                    source_path=result.source_path,
                    doc_kind=result.doc_kind,
                    stage="text_ready" if result.doc_kind == "text" else "table_ready",
                    status="completed",
                    chunk_count=result.text_chunk_count,
                    table_record_count=result.table_record_count,
                )
                self._work_queue(group_id).enqueue_document(
                    build_id=build_id,
                    doc_id=result.doc_id,
                    source_path=result.source_path,
                    stage="completed",
                    status="completed",
                )

        scanned_count = len(source_documents)
        last_seen_file = source_documents[-1].source_path if source_documents else ""
        last_seen_hash = source_documents[-1].revision if source_documents else ""

        state_store.write_scan_checkpoint(
            build_id=build_id,
            group_id=group_id,
            namespace="knowledge",
            build_input_fingerprint=source_fingerprint,
            last_seen_file=last_seen_file,
            last_seen_revision=last_seen_hash,
            scanned_file_count=scanned_count,
            status="completed",
        )

        chunk_tuple = tuple(all_chunks)
        chunk_store = ChunkStore(candidate_dir / "chunk_store.sqlite")
        chunk_store.upsert_chunks(chunk_tuple)
        self._rebuild_pool(candidate_dir / "text_pool", tuple(text_chunks))
        self._rebuild_pool(candidate_dir / "table_pool", tuple(table_chunks))
        (candidate_dir / "chunk_meta.json").write_text(json.dumps(chunk_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        (candidate_dir / "build_fingerprint.json").write_text(
            json.dumps({"fingerprint": source_fingerprint, "source_ids": list(request.source_ids)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        state_store.write_index_checkpoint(
            build_id=build_id,
            group_id=group_id,
            namespace="knowledge",
            text_lexical_ready=True,
            text_vector_ready=True,
            table_lexical_ready=True,
            table_vector_ready=True,
            chunk_count=len(text_chunks),
            table_summary_count=len(table_chunks),
        )

        validation_result = self._validate_candidate(
            candidate_dir=candidate_dir,
            source_documents=source_documents,
            chunk_meta=chunk_meta,
            text_chunk_count=len(text_chunks),
            table_record_count=len(table_chunks),
            doc_results=tuple(doc_results),
        )
        state_store.append_validation_history(
            {
                "build_id": build_id,
                "group_id": group_id,
                "namespace": "knowledge",
                "status": "passed" if validation_result["passed"] else "failed",
                **validation_result,
            }
        )
        if not bool(validation_result["passed"]):
            state_store.append_build(request, status="failed")
            self._work_queue(group_id).enqueue_build(
                build_id=build_id,
                namespace="knowledge",
                group_id=group_id,
                user_id=None,
                mode=mode,
                status="failed",
            )
            raise ValueError(
                "candidate validation failed: "
                f"blocking_errors={validation_result['blocking_errors']}, warnings={validation_result['warnings']}"
            )
        state_store.append_build(request, status="validated")
        snapshot_id = f"s_{build_id}"
        self._snapshot_from_candidate(group_id, candidate_dir, snapshot_id)
        self._promote_candidate_to_latest(group_id, candidate_dir, build_id)
        self._promote_candidate_to_current(group_id, candidate_dir)
        manifest_store.activate(
            "knowledge",
            current_build_id=build_id,
            current_snapshot_id=snapshot_id,
            previous_snapshot_id=manifest.current_snapshot_id,
        )
        state_store.write_activation_checkpoint(
            build_id=build_id,
            snapshot_id=snapshot_id,
            snapshot_created=True,
            current_promoted=True,
            manifest_activated=True,
        )
        state_store.append_build(request, status="activated")
        state_store.append_build_history(
            {
                "build_id": build_id,
                "group_id": group_id,
                "namespace": "knowledge",
                "source_count": len(source_documents),
                "text_chunk_count": len(text_chunks),
                "table_record_count": len(table_chunks),
                "snapshot_id": snapshot_id,
                "candidate_dir": str(candidate_dir),
                "current_build_id": build_id,
                "doc_results": doc_results,
                "build_input_fingerprint": source_fingerprint,
                "validation": validation_result,
            }
        )
        self._work_queue(group_id).enqueue_build(
            build_id=build_id,
            namespace="knowledge",
            group_id=group_id,
            user_id=None,
            mode=mode,
            status="activated",
        )
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
        return StateStore(registries_dir=self.storage_groups_dir / group_id / "registries")

    def _work_queue(self, group_id: str) -> WorkQueue:
        return WorkQueue(self.storage_groups_dir / group_id / "registries" / "work_queue.sqlite")

    def _source_registry_path(self, group_id: str) -> Path:
        path = self.storage_groups_dir / group_id / "registries" / "history" / "source_registry.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _current_dir(self, group_id: str) -> Path:
        path = self.storage_groups_dir / group_id / "knowledge" / "indexes" / "current"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _builds_root(self, group_id: str) -> Path:
        path = self.storage_groups_dir / group_id / "knowledge" / "indexes" / "builds"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _running_builds_root(self, group_id: str) -> Path:
        path = self._builds_root(group_id) / "running"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _latest_builds_root(self, group_id: str) -> Path:
        path = self._builds_root(group_id) / "latest"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _candidate_dir(self, group_id: str, build_id: str) -> Path:
        return self._running_builds_root(group_id) / build_id

    def _snapshots_root(self, group_id: str) -> Path:
        path = self.storage_groups_dir / group_id / "knowledge" / "indexes" / "snapshots"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _snapshot_dir(self, group_id: str, snapshot_id: str) -> Path:
        return self._snapshots_root(group_id) / snapshot_id

    def _prepare_candidate_layout(self, candidate_dir: Path) -> None:
        for pool in ("text_pool", "table_pool"):
            (candidate_dir / pool / "lexical").mkdir(parents=True, exist_ok=True)
            (candidate_dir / pool / "vector").mkdir(parents=True, exist_ok=True)

    def _rebuild_pool(self, pool_dir: Path, chunks: tuple) -> None:
        lexical = LexicalIndex(pool_dir / "lexical" / "term_postings.sqlite", pool_dir / "lexical" / "globals.json")
        vector = SimpleVectorIndex(pool_dir / "vector" / "index.sqlite")
        lexical.rebuild(chunks)
        vector.rebuild(chunks)

    def _promote_candidate_to_latest(self, group_id: str, candidate_dir: Path, build_id: str) -> None:
        latest_dir = self._latest_builds_root(group_id) / build_id
        self._copy_tree_contents(candidate_dir, latest_dir)

    def _promote_candidate_to_current(self, group_id: str, candidate_dir: Path) -> None:
        current_dir = self._current_dir(group_id)
        self._copy_tree_contents(candidate_dir, current_dir)

    def _snapshot_from_candidate(self, group_id: str, candidate_dir: Path, snapshot_id: str) -> None:
        snapshot_dir = self._snapshot_dir(group_id, snapshot_id)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._copy_tree_contents(candidate_dir, snapshot_dir)
        (snapshot_dir / "manifest.json").write_text(
            json.dumps(
                IndexManifest(
                    namespace="knowledge",
                    current_build_id=candidate_dir.name,
                    current_snapshot_id=snapshot_id,
                    previous_snapshot_id=None,
                ).to_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _copy_tree_contents(self, source_dir: Path, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in source_dir.rglob("*"):
            relative = path.relative_to(source_dir)
            target = target_dir / relative
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

    def _write_source_registry(self, group_id: str, *, request: BuildRequest, source_documents: tuple, state_store: StateStore) -> None:
        now = datetime.now().isoformat()
        payload = {
            "build_id": request.build_id,
            "group_id": request.group_id,
            "namespace": request.namespace,
            "build_input_fingerprint": request.source_fingerprint,
            "source_ids": list(request.source_ids),
            "sources": [
                {
                    "source_id": source.source_id,
                    "source_path": source.source_path,
                    "file_type": source.file_type,
                    "revision": source.revision,
                    "scan_status": "done",
                    "discovered_at": now,
                    "scanned_at": now,
                    "scan_error": None,
                }
                for source in source_documents
            ],
        }
        state_store.append_source_registry(payload)

    def _load_assets(self, current_dir: Path) -> GroupKnowledgeAssets:
        chunk_meta_path = current_dir / "chunk_meta.json"
        return GroupKnowledgeAssets(
            chunk_store=ChunkStore(current_dir / "chunk_store.sqlite"),
            text_lexical=LexicalIndex(current_dir / "text_pool" / "lexical" / "term_postings.sqlite", current_dir / "text_pool" / "lexical" / "globals.json"),
            text_vector=SimpleVectorIndex(current_dir / "text_pool" / "vector" / "index.sqlite"),
            table_lexical=LexicalIndex(current_dir / "table_pool" / "lexical" / "term_postings.sqlite", current_dir / "table_pool" / "lexical" / "globals.json"),
            table_vector=SimpleVectorIndex(current_dir / "table_pool" / "vector" / "index.sqlite"),
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

    def _document_worker_count(self, source_count: int) -> int:
        if source_count <= 1:
            return 1
        cpu_workers = os.cpu_count() or 4
        return max(2, min(source_count, cpu_workers, 8))

    def _process_source_document(self, source) -> DocumentBuildResult:
        doc_id = self._doc_id_for_source(source.source_path)
        doc_kind = self._doc_kind_for_source(source.file_type)
        try:
            parsed = self.parser.parse(doc_id, source)
            normalized = self.normalizer.normalize(parsed)
            doc_chunks = tuple(self.chunker.chunk(normalized))
            validation = self._validate_document_outputs(source=source, doc_kind=doc_kind, doc_chunks=doc_chunks)
            if validation["blocking_errors"]:
                return DocumentBuildResult(
                    source_id=source.source_id,
                    source_path=source.source_path,
                    doc_id=doc_id,
                    doc_kind=doc_kind,
                    status="failed",
                    doc_chunks=(),
                    text_chunk_count=0,
                    table_record_count=0,
                    warnings=tuple(validation["warnings"]),
                    error="; ".join(str(item) for item in validation["blocking_errors"]),
                )
            return DocumentBuildResult(
                source_id=source.source_id,
                source_path=source.source_path,
                doc_id=doc_id,
                doc_kind=doc_kind,
                status="completed",
                doc_chunks=doc_chunks,
                text_chunk_count=int(validation["text_chunk_count"]),
                table_record_count=int(validation["table_record_count"]),
                warnings=tuple(str(item) for item in validation["warnings"]),
            )
        except Exception as exc:
            return DocumentBuildResult(
                source_id=source.source_id,
                source_path=source.source_path,
                doc_id=doc_id,
                doc_kind=doc_kind,
                status="failed",
                doc_chunks=(),
                text_chunk_count=0,
                table_record_count=0,
                warnings=(),
                error=str(exc),
            )

    def _doc_kind_for_source(self, file_type: str) -> str:
        return "table" if file_type.lower() in {"xlsx", "xls", "csv", "tsv"} else "text"

    def _validate_document_outputs(self, *, source, doc_kind: str, doc_chunks: tuple) -> dict[str, object]:
        blocking_errors: list[str] = []
        warnings: list[str] = []
        text_chunk_count = sum(1 for chunk in doc_chunks if not bool(chunk.metadata.get("structured_only")))
        table_record_count = len(doc_chunks) - text_chunk_count
        if doc_kind == "table":
            if not any(bool(chunk.metadata.get("structured_only")) for chunk in doc_chunks):
                blocking_errors.append(f"table source produced no summary records: {source.source_path}")
            return {
                "blocking_errors": blocking_errors,
                "warnings": warnings,
                "text_chunk_count": text_chunk_count,
                "table_record_count": table_record_count,
            }
        if text_chunk_count <= 0:
            warnings.append(f"text source produced no chunks: {source.source_path}")
        return {
            "blocking_errors": blocking_errors,
            "warnings": warnings,
            "text_chunk_count": text_chunk_count,
            "table_record_count": table_record_count,
        }

    def _validate_candidate(
        self,
        *,
        candidate_dir: Path,
        source_documents: tuple,
        chunk_meta: dict[str, dict[str, object]],
        text_chunk_count: int,
        table_record_count: int,
        doc_results: tuple[dict[str, object], ...],
    ) -> dict[str, object]:
        required_files = (
            candidate_dir / "chunk_store.sqlite",
            candidate_dir / "chunk_meta.json",
            candidate_dir / "build_fingerprint.json",
            candidate_dir / "text_pool" / "lexical" / "term_postings.sqlite",
            candidate_dir / "text_pool" / "lexical" / "globals.json",
            candidate_dir / "text_pool" / "vector" / "index.sqlite",
            candidate_dir / "table_pool" / "lexical" / "term_postings.sqlite",
            candidate_dir / "table_pool" / "lexical" / "globals.json",
            candidate_dir / "table_pool" / "vector" / "index.sqlite",
        )
        missing = [str(path) for path in required_files if not path.exists()]
        blocking_errors = [f"missing required asset: {path}" for path in missing]
        warnings: list[str] = []
        source_counts: dict[str, int] = {}
        table_sources: set[str] = set()
        for chunk in chunk_meta.values():
            source_path = str(chunk.get("source_path") or "")
            source_counts[source_path] = source_counts.get(source_path, 0) + 1
            if bool(chunk.get("structured_only")):
                table_sources.add(source_path)
        failed_sources = {
            str(result.get("source_path") or "")
            for result in doc_results
            if str(result.get("status") or "") == "failed"
        }
        warnings.extend(
            warning
            for result in doc_results
            for warning in list(result.get("warnings") or [])
            if str(warning).strip()
        )
        for source in source_documents:
            count = source_counts.get(source.source_path, 0)
            if self._doc_kind_for_source(source.file_type) == "table":
                if source.source_path not in table_sources:
                    blocking_errors.append(f"table source missing structured output: {source.source_path}")
            elif source.source_path in failed_sources:
                blocking_errors.append(f"text source failed during document task: {source.source_path}")
            elif count <= 0:
                warnings.append(f"text source missing indexable output: {source.source_path}")
        if text_chunk_count + table_record_count <= 0:
            blocking_errors.append("no indexable artifacts produced for candidate build")
        passed = not blocking_errors
        return {
            "passed": passed,
            "source_count": len(source_documents),
            "text_chunk_count": text_chunk_count,
            "table_record_count": table_record_count,
            "blocking_errors": blocking_errors,
            "warnings": warnings,
            "metrics": {
                "source_count": len(source_documents),
                "doc_completed_count": sum(1 for result in doc_results if str(result.get("status") or "") == "completed"),
                "doc_failed_count": sum(1 for result in doc_results if str(result.get("status") or "") == "failed"),
                "warning_count": len(warnings),
                "table_source_count": sum(1 for source in source_documents if self._doc_kind_for_source(source.file_type) == "table"),
                "text_source_count": sum(1 for source in source_documents if self._doc_kind_for_source(source.file_type) == "text"),
            },
        }

    def _new_build_id(self, group_id: str) -> str:
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        compact_group = group_id[:3] if group_id else "grp"
        suffix = uuid.uuid4().hex[:6]
        return f"b_{compact_group}_{timestamp}_{suffix}"

    def _current_timestamp(self) -> float:
        import time

        return time.time()
