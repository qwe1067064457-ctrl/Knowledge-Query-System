from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal


BuildMode = Literal["full", "incremental", "resume"]
BuildStatus = Literal["pending", "running", "failed", "validated", "activated", "rolled_back"]
SourceKind = Literal["knowledge", "daily_log", "domain_case"]


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    group_id: str
    user_id: str | None
    namespace: str
    source_kind: SourceKind
    source_path: str
    file_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    revision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedDocument:
    doc_id: str
    source: SourceDocument
    title: str | None
    sections: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source"] = self.source.to_dict()
        return payload


@dataclass(frozen=True)
class NormalizedDocument:
    doc_id: str
    group_id: str
    user_id: str | None
    namespace: str
    source_kind: SourceKind
    source_path: str
    file_type: str
    title: str | None
    sections: tuple[dict[str, Any], ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    revision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChunkDocument:
    chunk_id: str
    doc_id: str
    group_id: str
    user_id: str | None
    namespace: str
    source_kind: SourceKind
    source_path: str
    file_type: str
    content: str
    locator: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    revision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BuildRequest:
    build_id: str
    group_id: str
    namespace: str
    mode: BuildMode
    source_ids: tuple[str, ...]
    source_fingerprint: str
    candidate_dir: str
    user_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def build_input_fingerprint(self) -> str:
        return self.source_fingerprint


@dataclass(frozen=True)
class BuildCheckpoint:
    source_id: str
    build_id: str
    group_id: str
    namespace: str
    user_id: str | None
    scan_checkpoint: dict[str, Any]
    doc_local_progress: dict[str, Any]
    pipeline_progress: dict[str, Any]
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IndexManifest:
    namespace: str
    current_build_id: str | None = None
    current_snapshot_id: str | None = None
    previous_snapshot_id: str | None = None
    activated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
