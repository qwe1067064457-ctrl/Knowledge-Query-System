from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import uuid

from context.models import MemoryEntry
from retrieval_infra.adapters import MemorySourceAdapter
from retrieval_infra.chunking import TextChunker
from retrieval_infra.contracts import BuildRequest, IndexManifest
from retrieval_infra.indexing.chunk_store import ChunkStore
from retrieval_infra.indexing.lexical_index import LexicalIndex
from retrieval_infra.indexing.manifest_store import ManifestStore
from retrieval_infra.indexing.state_store import StateStore
from retrieval_infra.indexing.vector_index import SimpleVectorIndex
from retrieval_infra.normalization import DocumentNormalizer
from retrieval_infra.parsing import SimpleTextParser
from retrieval_infra.queue import WorkQueue


@dataclass(frozen=True)
class MemoryEntryBuildResult:
    entry_id: str
    source_path: str
    memory_type: str
    status: str
    entry_chunks: tuple
    chunk_count: int
    warnings: tuple[str, ...]
    error: str | None = None


class MemoryIndexManager:
    def __init__(self, base_storage_path: Path) -> None:
        self.base_storage_path = Path(base_storage_path)
        self.adapter = MemorySourceAdapter()
        self.parser = SimpleTextParser()
        self.normalizer = DocumentNormalizer()
        self.chunker = TextChunker()

    def ensure_built(self, *, group_id: str, user_id: str, memory_entries: list[MemoryEntry]) -> bool:
        current_dir = self._current_dir(group_id, user_id)
        current_fingerprint = self._load_current_fingerprint(current_dir)
        next_fingerprint = self._fingerprint_entries(memory_entries)
        if current_fingerprint == next_fingerprint and (current_dir / "chunk_store.sqlite").exists():
            return True
        try:
            self.rebuild(group_id=group_id, user_id=user_id, memory_entries=memory_entries, mode="full")
            return True
        except Exception:
            if (current_dir / "chunk_store.sqlite").exists():
                return False
            raise

    def rebuild(self, *, group_id: str, user_id: str, memory_entries: list[MemoryEntry], mode: str = "full") -> None:
        manifest_store = self._manifest_store(group_id, user_id)
        manifest = manifest_store.load("memory")
        build_id = self._new_build_id(group_id, user_id)
        candidate_dir = self._candidate_dir(group_id, user_id, build_id)
        candidate_dir.mkdir(parents=True, exist_ok=True)
        self._prepare_candidate_layout(candidate_dir)

        build_input_fingerprint = self._fingerprint_entries(memory_entries)
        request = BuildRequest(
            build_id=build_id,
            group_id=group_id,
            namespace="memory",
            mode=mode,  # type: ignore[arg-type]
            source_ids=tuple(self._entry_id(entry) for entry in memory_entries),
            source_fingerprint=build_input_fingerprint,
            candidate_dir=str(candidate_dir),
            user_id=user_id,
        )

        state_store = self._state_store(group_id, user_id)
        work_queue = self._work_queue(group_id, user_id)
        state_store.append_build(request, status="running")
        self._write_source_registry(
            group_id=group_id,
            user_id=user_id,
            request=request,
            memory_entries=memory_entries,
            state_store=state_store,
        )
        work_queue.enqueue_build(
            build_id=build_id,
            namespace="memory",
            group_id=group_id,
            user_id=user_id,
            mode=mode,
            status="running",
        )
        state_store.write_scan_checkpoint(
            build_id=build_id,
            group_id=group_id,
            namespace="memory",
            build_input_fingerprint=build_input_fingerprint,
            last_seen_file=memory_entries[-1].source if memory_entries else "",
            last_seen_revision=self._entry_revision(memory_entries[-1]) if memory_entries else "",
            scanned_file_count=len(memory_entries),
            status="completed",
        )

        all_chunks = []
        chunk_meta: dict[str, dict[str, object]] = {}
        entry_results: list[dict[str, object]] = []
        worker_count = self._entry_worker_count(len(memory_entries))
        for entry in memory_entries:
            entry_id = self._entry_id(entry)
            work_queue.enqueue_entry(
                build_id=build_id,
                entry_id=entry_id,
                source_path=entry.source,
                stage="running",
                status="running",
            )
            state_store.write_entry_checkpoint(
                build_id=build_id,
                entry_id=entry_id,
                source_id=entry_id,
                source_path=entry.source,
                memory_type=entry.memory_type,
                stage="started",
                status="running",
            )

        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix=f"mem-{group_id}-{user_id}") as executor:
            future_map = {executor.submit(self._process_memory_entry, entry): entry for entry in memory_entries}
            for future in as_completed(future_map):
                entry = future_map[future]
                result = future.result()
                entry_results.append(
                    {
                        "entry_id": result.entry_id,
                        "source_path": result.source_path,
                        "memory_type": result.memory_type,
                        "status": result.status,
                        "chunk_count": result.chunk_count,
                        "warnings": list(result.warnings),
                        "error": result.error,
                    }
                )
                if result.status != "completed":
                    state_store.write_entry_checkpoint(
                        build_id=build_id,
                        entry_id=result.entry_id,
                        source_id=result.entry_id,
                        source_path=result.source_path,
                        memory_type=result.memory_type,
                        stage="failed",
                        status="failed",
                        error=result.error or "entry task failed",
                    )
                    work_queue.enqueue_entry(
                        build_id=build_id,
                        entry_id=result.entry_id,
                        source_path=result.source_path,
                        stage="failed",
                        status="failed",
                    )
                    continue
                entry_locator = self._entry_locator(entry)
                for chunk in result.entry_chunks:
                    all_chunks.append(chunk)
                    chunk_meta[chunk.chunk_id] = {
                        "source_path": chunk.source_path,
                        "locator": entry_locator,
                        "memory_id": chunk.metadata.get("memory_id"),
                        "memory_type": chunk.metadata.get("memory_type"),
                        "source_session_id": chunk.metadata.get("source_session_id"),
                    }
                state_store.write_entry_checkpoint(
                    build_id=build_id,
                    entry_id=result.entry_id,
                    source_id=result.entry_id,
                    source_path=result.source_path,
                    memory_type=result.memory_type,
                    stage="completed",
                    status="completed",
                    chunk_count=result.chunk_count,
                )
                work_queue.enqueue_entry(
                    build_id=build_id,
                    entry_id=result.entry_id,
                    source_path=result.source_path,
                    stage="completed",
                    status="completed",
                )

        chunk_tuple = tuple(all_chunks)
        chunk_store = ChunkStore(candidate_dir / "chunk_store.sqlite")
        chunk_store.upsert_chunks(chunk_tuple)
        lexical = LexicalIndex(candidate_dir / "lexical" / "term_postings.sqlite", candidate_dir / "lexical" / "globals.json")
        vector = SimpleVectorIndex(candidate_dir / "vector" / "index.sqlite")
        lexical.rebuild(chunk_tuple)
        vector.rebuild(chunk_tuple)
        (candidate_dir / "chunk_meta.json").write_text(json.dumps(chunk_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        (candidate_dir / "build_fingerprint.json").write_text(
            json.dumps({"fingerprint": build_input_fingerprint, "source_ids": list(request.source_ids)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        state_store.write_index_checkpoint(
            build_id=build_id,
            group_id=group_id,
            namespace="memory",
            text_lexical_ready=True,
            text_vector_ready=True,
            table_lexical_ready=False,
            table_vector_ready=False,
            chunk_count=len(chunk_tuple),
            table_summary_count=0,
            status="completed",
        )

        validation_result = self._validate_candidate(
            candidate_dir=candidate_dir,
            memory_entries=memory_entries,
            chunk_meta=chunk_meta,
            chunk_count=len(chunk_tuple),
            entry_results=tuple(entry_results),
        )
        state_store.append_validation_history(
            {
                "build_id": build_id,
                "group_id": group_id,
                "user_id": user_id,
                "namespace": "memory",
                "status": "passed" if validation_result["passed"] else "failed",
                **validation_result,
            }
        )
        if not bool(validation_result["passed"]):
            state_store.append_build(request, status="failed")
            work_queue.enqueue_build(
                build_id=build_id,
                namespace="memory",
                group_id=group_id,
                user_id=user_id,
                mode=mode,
                status="failed",
            )
            raise ValueError(
                "memory candidate validation failed: "
                f"blocking_errors={validation_result['blocking_errors']}, warnings={validation_result['warnings']}"
            )

        state_store.append_build(request, status="validated")
        snapshot_id = f"s_{build_id}"
        self._snapshot_from_candidate(group_id, user_id, candidate_dir, snapshot_id)
        self._promote_candidate_to_latest(group_id, user_id, candidate_dir, build_id)
        self._promote_candidate_to_current(group_id, user_id, candidate_dir)
        manifest_store.activate(
            "memory",
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
                "user_id": user_id,
                "namespace": "memory",
                "entry_count": len(memory_entries),
                "chunk_count": len(chunk_tuple),
                "snapshot_id": snapshot_id,
                "candidate_dir": str(candidate_dir),
                "current_build_id": build_id,
                "entry_results": entry_results,
                "build_input_fingerprint": build_input_fingerprint,
                "validation": validation_result,
            }
        )
        work_queue.enqueue_build(
            build_id=build_id,
            namespace="memory",
            group_id=group_id,
            user_id=user_id,
            mode=mode,
            status="activated",
        )

    def load_assets(self, group_id: str, user_id: str) -> dict[str, Path]:
        current_dir = self._current_dir(group_id, user_id)
        return {
            "current_dir": current_dir,
            "chunk_store": current_dir / "chunk_store.sqlite",
            "chunk_meta": current_dir / "chunk_meta.json",
            "lexical_dir": current_dir / "lexical",
            "vector_dir": current_dir / "vector",
        }

    def _process_memory_entry(self, entry: MemoryEntry) -> MemoryEntryBuildResult:
        entry_id = self._entry_id(entry)
        try:
            source = self.adapter.build_source_document(
                source_id=entry_id,
                group_id=entry.group_id,
                user_id=entry.user_id or "default",
                source_kind=entry.memory_type,
                source_path=entry.source,
                content=self._entry_content(entry),
                metadata={
                    "title": entry.title or entry.subject or entry.memory_type,
                    "subject": entry.subject,
                    "memory_id": entry_id,
                    "memory_type": entry.memory_type,
                    "source_session_id": entry.source_session_id,
                    "entry_locator": self._entry_locator(entry),
                },
                revision=self._entry_revision(entry),
            )
            parsed = self.parser.parse(f"doc_{entry_id}", source)
            normalized = self.normalizer.normalize(parsed)
            chunks = tuple(self.chunker.chunk(normalized))
            if not chunks:
                return MemoryEntryBuildResult(
                    entry_id=entry_id,
                    source_path=entry.source,
                    memory_type=entry.memory_type,
                    status="failed",
                    entry_chunks=(),
                    chunk_count=0,
                    warnings=(),
                    error=f"entry produced no chunks: {entry.source}",
                )
            return MemoryEntryBuildResult(
                entry_id=entry_id,
                source_path=entry.source,
                memory_type=entry.memory_type,
                status="completed",
                entry_chunks=chunks,
                chunk_count=len(chunks),
                warnings=(),
            )
        except Exception as exc:
            return MemoryEntryBuildResult(
                entry_id=entry_id,
                source_path=entry.source,
                memory_type=entry.memory_type,
                status="failed",
                entry_chunks=(),
                chunk_count=0,
                warnings=(),
                error=str(exc),
            )

    def _validate_candidate(
        self,
        *,
        candidate_dir: Path,
        memory_entries: list[MemoryEntry],
        chunk_meta: dict[str, dict[str, object]],
        chunk_count: int,
        entry_results: tuple[dict[str, object], ...],
    ) -> dict[str, object]:
        required_files = (
            candidate_dir / "chunk_store.sqlite",
            candidate_dir / "chunk_meta.json",
            candidate_dir / "build_fingerprint.json",
            candidate_dir / "lexical" / "term_postings.sqlite",
            candidate_dir / "lexical" / "globals.json",
            candidate_dir / "vector" / "index.sqlite",
        )
        blocking_errors = [f"missing required asset: {path}" for path in required_files if not path.exists()]
        warnings: list[str] = []
        source_counts: dict[str, int] = {}
        failed_entries: set[str] = set()
        for chunk in chunk_meta.values():
            memory_id = str(chunk.get("memory_id") or "")
            source_counts[memory_id] = source_counts.get(memory_id, 0) + 1
        for result in entry_results:
            for warning in list(result.get("warnings") or []):
                if str(warning).strip():
                    warnings.append(str(warning))
            if str(result.get("status") or "") == "failed":
                failed_entries.add(str(result.get("entry_id") or ""))
        for entry in memory_entries:
            entry_id = self._entry_id(entry)
            if entry_id in failed_entries:
                blocking_errors.append(f"entry failed during build: {entry.source}#{entry_id}")
            elif source_counts.get(entry_id, 0) <= 0:
                blocking_errors.append(f"entry missing chunk output: {entry.source}#{entry_id}")
        if chunk_count <= 0:
            blocking_errors.append("no indexable memory chunks produced for candidate build")
        smoke_error = self._smoke_validate(candidate_dir, chunk_meta)
        if smoke_error:
            blocking_errors.append(smoke_error)
        return {
            "passed": not blocking_errors,
            "entry_count": len(memory_entries),
            "chunk_count": chunk_count,
            "blocking_errors": blocking_errors,
            "warnings": warnings,
            "metrics": {
                "entry_count": len(memory_entries),
                "entry_completed_count": sum(1 for result in entry_results if str(result.get("status") or "") == "completed"),
                "entry_failed_count": sum(1 for result in entry_results if str(result.get("status") or "") == "failed"),
                "warning_count": len(warnings),
            },
        }

    def _smoke_validate(self, candidate_dir: Path, chunk_meta: dict[str, dict[str, object]]) -> str | None:
        if not chunk_meta:
            return "smoke retrieval unavailable because chunk metadata is empty"
        first_chunk_id = next(iter(chunk_meta.keys()))
        content = ChunkStore(candidate_dir / "chunk_store.sqlite").get_chunk_content(first_chunk_id) or ""
        tokens = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", content.lower())
        if not tokens:
            return None
        lexical = LexicalIndex(candidate_dir / "lexical" / "term_postings.sqlite", candidate_dir / "lexical" / "globals.json")
        if not lexical.query(tokens[0], top_k=1):
            return "smoke retrieval failed on candidate lexical index"
        return None

    def _write_source_registry(
        self,
        *,
        group_id: str,
        user_id: str,
        request: BuildRequest,
        memory_entries: list[MemoryEntry],
        state_store: StateStore,
    ) -> None:
        now = datetime.now().isoformat()
        payload = {
            "build_id": request.build_id,
            "group_id": group_id,
            "user_id": user_id,
            "namespace": request.namespace,
            "build_input_fingerprint": request.source_fingerprint,
            "source_ids": list(request.source_ids),
            "sources": [
                {
                    "source_id": self._entry_id(entry),
                    "source_path": entry.source,
                    "file_type": "memory_text",
                    "revision": self._entry_revision(entry),
                    "memory_type": entry.memory_type,
                    "entry_locator": self._entry_locator(entry),
                    "scan_status": "done",
                    "discovered_at": now,
                    "scanned_at": now,
                    "scan_error": None,
                }
                for entry in memory_entries
            ],
        }
        state_store.append_source_registry(payload)

    def _entry_content(self, entry: MemoryEntry) -> str:
        return "\n".join(part for part in (entry.title or "", entry.subject or "", entry.content) if part).strip()

    def _entry_locator(self, entry: MemoryEntry) -> dict[str, Any]:
        if entry.metadata and entry.metadata.get("entry_locator"):
            return dict(entry.metadata["entry_locator"])
        return {"line_no": 1}

    def _entry_revision(self, entry: MemoryEntry) -> str:
        if entry.metadata and entry.metadata.get("revision"):
            return str(entry.metadata["revision"])
        return entry.timestamp.isoformat()

    def _fingerprint_entries(self, entries: list[MemoryEntry]) -> str:
        digest = hashlib.md5()
        for entry in sorted(
            entries,
            key=lambda item: (
                item.memory_type,
                self._entry_id(item),
                item.timestamp.isoformat(),
                item.title or "",
                item.subject or "",
                item.content,
            ),
        ):
            digest.update(self._entry_id(entry).encode("utf-8"))
            digest.update(entry.memory_type.encode("utf-8"))
            digest.update(entry.timestamp.isoformat().encode("utf-8"))
            digest.update((entry.title or "").encode("utf-8"))
            digest.update((entry.subject or "").encode("utf-8"))
            digest.update(entry.content.encode("utf-8"))
        return digest.hexdigest()

    def _load_current_fingerprint(self, current_dir: Path) -> str:
        fingerprint_path = current_dir / "build_fingerprint.json"
        if not fingerprint_path.exists():
            return ""
        raw = fingerprint_path.read_text(encoding="utf-8").strip()
        if not raw:
            return ""
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                return str(payload.get("fingerprint") or "")
        except json.JSONDecodeError:
            return raw
        return ""

    def _entry_id(self, entry: MemoryEntry) -> str:
        if entry.metadata and entry.metadata.get("id"):
            return str(entry.metadata["id"])
        return hashlib.md5(
            f"{entry.memory_type}:{entry.group_id}:{entry.user_id}:{entry.title}:{entry.subject}:{entry.content}".encode("utf-8")
        ).hexdigest()

    def _index_root(self, group_id: str, user_id: str) -> Path:
        path = self.base_storage_path / "groups" / group_id / "users" / user_id / "indexes" / "memory"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _current_dir(self, group_id: str, user_id: str) -> Path:
        path = self._index_root(group_id, user_id) / "current"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _builds_root(self, group_id: str, user_id: str) -> Path:
        path = self._index_root(group_id, user_id) / "builds"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _running_builds_root(self, group_id: str, user_id: str) -> Path:
        path = self._builds_root(group_id, user_id) / "running"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _latest_builds_root(self, group_id: str, user_id: str) -> Path:
        path = self._builds_root(group_id, user_id) / "latest"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _candidate_dir(self, group_id: str, user_id: str, build_id: str) -> Path:
        return self._running_builds_root(group_id, user_id) / build_id

    def _snapshots_root(self, group_id: str, user_id: str) -> Path:
        path = self._index_root(group_id, user_id) / "snapshots"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _snapshot_dir(self, group_id: str, user_id: str, snapshot_id: str) -> Path:
        return self._snapshots_root(group_id, user_id) / snapshot_id

    def _registries_dir(self, group_id: str, user_id: str) -> Path:
        path = self._index_root(group_id, user_id) / "registries"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _manifest_store(self, group_id: str, user_id: str) -> ManifestStore:
        return ManifestStore(self._registries_dir(group_id, user_id) / "index_manifest.json")

    def _state_store(self, group_id: str, user_id: str) -> StateStore:
        return StateStore(registries_dir=self._registries_dir(group_id, user_id), item_label="entry")

    def _work_queue(self, group_id: str, user_id: str) -> WorkQueue:
        return WorkQueue(self._registries_dir(group_id, user_id) / "work_queue.sqlite", item_label="entry")

    def _prepare_candidate_layout(self, candidate_dir: Path) -> None:
        (candidate_dir / "lexical").mkdir(parents=True, exist_ok=True)
        (candidate_dir / "vector").mkdir(parents=True, exist_ok=True)

    def _promote_candidate_to_latest(self, group_id: str, user_id: str, candidate_dir: Path, build_id: str) -> None:
        latest_dir = self._latest_builds_root(group_id, user_id) / build_id
        self._copy_tree_contents(candidate_dir, latest_dir)

    def _promote_candidate_to_current(self, group_id: str, user_id: str, candidate_dir: Path) -> None:
        current_dir = self._current_dir(group_id, user_id)
        self._copy_tree_contents(candidate_dir, current_dir)

    def _snapshot_from_candidate(self, group_id: str, user_id: str, candidate_dir: Path, snapshot_id: str) -> None:
        snapshot_dir = self._snapshot_dir(group_id, user_id, snapshot_id)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._copy_tree_contents(candidate_dir, snapshot_dir)
        (snapshot_dir / "manifest.json").write_text(
            json.dumps(
                IndexManifest(
                    namespace="memory",
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

    def _entry_worker_count(self, entry_count: int) -> int:
        if entry_count <= 1:
            return 1
        cpu_workers = os.cpu_count() or 4
        return max(2, min(entry_count, cpu_workers, 8))

    def _new_build_id(self, group_id: str, user_id: str) -> str:
        timestamp = datetime.now().strftime("%m%d%H%M%S")
        compact_group = group_id[:3] if group_id else "grp"
        compact_user = user_id[:3] if user_id else "usr"
        suffix = uuid.uuid4().hex[:6]
        return f"mb_{compact_group}_{compact_user}_{timestamp}_{suffix}"
