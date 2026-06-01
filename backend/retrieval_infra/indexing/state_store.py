from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from retrieval_infra.contracts import BuildCheckpoint, BuildRequest


class StateStore:
    """隔离的构建历史层与恢复层。

    - history/: 低频 append 的 JSONL 审计记录
    - recovery/: 高频更新的 sqlite 恢复状态
    """

    def __init__(
        self,
        *,
        registries_dir: Path | None = None,
        build_registry_path: Path | None = None,
        checkpoints_path: Path | None = None,
    ) -> None:
        if registries_dir is not None:
            self.registries_dir = Path(registries_dir)
        elif build_registry_path is not None:
            self.registries_dir = Path(build_registry_path).parent
        elif checkpoints_path is not None:
            self.registries_dir = Path(checkpoints_path).parent
        else:
            raise ValueError("registries_dir or legacy paths are required")

        self.registries_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir = self.registries_dir / "history"
        self.recovery_dir = self.registries_dir / "recovery"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.recovery_dir.mkdir(parents=True, exist_ok=True)

        self.build_registry_path = build_registry_path or (self.history_dir / "build_registry.jsonl")
        self.build_history_path = self.history_dir / "build_history.jsonl"
        self.validation_history_path = self.history_dir / "validation_history.jsonl"
        self.source_registry_path = self.history_dir / "source_registry.jsonl"

        self.scan_checkpoints_path = self.recovery_dir / "scan_checkpoints.sqlite"
        self.document_checkpoints_path = self.recovery_dir / "document_checkpoints.sqlite"
        self.index_checkpoints_path = self.recovery_dir / "index_checkpoints.sqlite"
        self.activation_checkpoints_path = self.recovery_dir / "activation_checkpoints.sqlite"

        self._ensure_recovery_schema()

    def append_build(self, request: BuildRequest, *, status: str) -> None:
        payload = request.to_dict() | {"status": status, "recorded_at": datetime.now().isoformat()}
        self._append_jsonl(self.build_registry_path, payload)

    def append_build_history(self, payload: dict[str, Any]) -> None:
        self._append_jsonl(self.build_history_path, payload | {"recorded_at": datetime.now().isoformat()})

    def append_validation_history(self, payload: dict[str, Any]) -> None:
        self._append_jsonl(self.validation_history_path, payload | {"recorded_at": datetime.now().isoformat()})

    def append_source_registry(self, payload: dict[str, Any]) -> None:
        self._append_jsonl(self.source_registry_path, payload | {"recorded_at": datetime.now().isoformat()})

    def write_scan_checkpoint(
        self,
        *,
        build_id: str,
        group_id: str,
        namespace: str,
        build_input_fingerprint: str,
        last_seen_file: str,
        last_seen_revision: str,
        scanned_file_count: int,
        status: str = "completed",
    ) -> None:
        payload = {
            "build_id": build_id,
            "group_id": group_id,
            "namespace": namespace,
            "build_input_fingerprint": build_input_fingerprint,
            "last_seen_file": last_seen_file,
            "last_seen_revision": last_seen_revision,
            "scanned_file_count": scanned_file_count,
            "status": status,
        }
        self._upsert_checkpoint(
            self.scan_checkpoints_path,
            table_name="scan_checkpoints",
            key_columns=("build_id",),
            key_values=(build_id,),
            payload=payload,
        )

    def write_document_checkpoint(
        self,
        *,
        build_id: str,
        doc_id: str,
        source_id: str,
        source_path: str,
        doc_kind: str,
        stage: str,
        status: str,
        chunk_count: int = 0,
        table_record_count: int = 0,
        error: str | None = None,
    ) -> None:
        payload = {
            "build_id": build_id,
            "doc_id": doc_id,
            "source_id": source_id,
            "source_path": source_path,
            "doc_kind": doc_kind,
            "stage": stage,
            "status": status,
            "chunk_count": chunk_count,
            "table_record_count": table_record_count,
            "error": error,
        }
        self._upsert_checkpoint(
            self.document_checkpoints_path,
            table_name="document_checkpoints",
            key_columns=("build_id", "doc_id"),
            key_values=(build_id, doc_id),
            payload=payload,
        )

    def write_index_checkpoint(
        self,
        *,
        build_id: str,
        group_id: str,
        namespace: str,
        text_lexical_ready: bool,
        text_vector_ready: bool,
        table_lexical_ready: bool,
        table_vector_ready: bool,
        chunk_count: int,
        table_summary_count: int,
        status: str = "completed",
    ) -> None:
        payload = {
            "build_id": build_id,
            "group_id": group_id,
            "namespace": namespace,
            "text_lexical_ready": text_lexical_ready,
            "text_vector_ready": text_vector_ready,
            "table_lexical_ready": table_lexical_ready,
            "table_vector_ready": table_vector_ready,
            "chunk_count": chunk_count,
            "table_summary_count": table_summary_count,
            "status": status,
        }
        self._upsert_checkpoint(
            self.index_checkpoints_path,
            table_name="index_checkpoints",
            key_columns=("build_id",),
            key_values=(build_id,),
            payload=payload,
        )

    def write_activation_checkpoint(
        self,
        *,
        build_id: str,
        snapshot_id: str,
        snapshot_created: bool,
        current_promoted: bool,
        manifest_activated: bool,
    ) -> None:
        payload = {
            "build_id": build_id,
            "snapshot_id": snapshot_id,
            "snapshot_created": snapshot_created,
            "current_promoted": current_promoted,
            "manifest_activated": manifest_activated,
        }
        self._upsert_checkpoint(
            self.activation_checkpoints_path,
            table_name="activation_checkpoints",
            key_columns=("build_id",),
            key_values=(build_id,),
            payload=payload,
        )

    def write_checkpoint(self, checkpoint: BuildCheckpoint) -> None:
        """兼容旧测试/旧调用：映射到 scan/document 两类恢复状态。"""
        scan = checkpoint.scan_checkpoint or {}
        self.write_scan_checkpoint(
            build_id=checkpoint.build_id,
            group_id=checkpoint.group_id,
            namespace=checkpoint.namespace,
            build_input_fingerprint=str(scan.get("build_input_fingerprint") or scan.get("last_seen_hash") or ""),
            last_seen_file=str(scan.get("last_seen_file") or ""),
            last_seen_revision=str(scan.get("last_seen_hash") or ""),
            scanned_file_count=int(scan.get("scanned_file_count") or 0),
            status=str(checkpoint.pipeline_progress.get("stage") or "completed"),
        )
        self.write_document_checkpoint(
            build_id=checkpoint.build_id,
            doc_id=str(checkpoint.doc_local_progress.get("doc_id") or checkpoint.source_id),
            source_id=checkpoint.source_id,
            source_path=str(scan.get("last_seen_file") or checkpoint.source_id),
            doc_kind=str(checkpoint.doc_local_progress.get("doc_kind") or "text"),
            stage=str(checkpoint.pipeline_progress.get("stage") or "unknown"),
            status="completed",
            chunk_count=int(checkpoint.pipeline_progress.get("chunked_docs") or 0),
            table_record_count=int(checkpoint.pipeline_progress.get("table_summary_count") or 0),
        )

    def load_scan_checkpoints(self) -> dict[str, dict[str, Any]]:
        return self._load_checkpoint_table(self.scan_checkpoints_path, "scan_checkpoints", ("build_id",))

    def load_document_checkpoints(self) -> dict[str, dict[str, Any]]:
        return self._load_checkpoint_table(self.document_checkpoints_path, "document_checkpoints", ("build_id", "doc_id"))

    def load_index_checkpoints(self) -> dict[str, dict[str, Any]]:
        return self._load_checkpoint_table(self.index_checkpoints_path, "index_checkpoints", ("build_id",))

    def load_activation_checkpoints(self) -> dict[str, dict[str, Any]]:
        return self._load_checkpoint_table(self.activation_checkpoints_path, "activation_checkpoints", ("build_id",))

    def _ensure_recovery_schema(self) -> None:
        self._ensure_checkpoint_db(self.scan_checkpoints_path, "scan_checkpoints", ("build_id TEXT PRIMARY KEY",))
        self._ensure_checkpoint_db(
            self.document_checkpoints_path,
            "document_checkpoints",
            ("build_id TEXT NOT NULL", "doc_id TEXT NOT NULL", "PRIMARY KEY (build_id, doc_id)"),
        )
        self._ensure_checkpoint_db(self.index_checkpoints_path, "index_checkpoints", ("build_id TEXT PRIMARY KEY",))
        self._ensure_checkpoint_db(self.activation_checkpoints_path, "activation_checkpoints", ("build_id TEXT PRIMARY KEY",))

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    @staticmethod
    def _ensure_checkpoint_db(db_path: Path, table_name: str, key_columns_sql: tuple[str, ...]) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {", ".join(key_columns_sql)},
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _upsert_checkpoint(
        db_path: Path,
        *,
        table_name: str,
        key_columns: tuple[str, ...],
        key_values: tuple[Any, ...],
        payload: dict[str, Any],
    ) -> None:
        updated_at = datetime.now().isoformat()
        columns = ", ".join([*key_columns, "payload_json", "updated_at"])
        placeholders = ", ".join(["?"] * (len(key_columns) + 2))
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})",
                (*key_values, json.dumps(payload, ensure_ascii=False), updated_at),
            )
            conn.commit()

    @staticmethod
    def _load_checkpoint_table(db_path: Path, table_name: str, key_columns: tuple[str, ...]) -> dict[str, dict[str, Any]]:
        if not db_path.exists():
            return {}
        key_expr = " || '::' || ".join(key_columns) if len(key_columns) > 1 else key_columns[0]
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(f"SELECT {key_expr}, payload_json FROM {table_name}").fetchall()
        output: dict[str, dict[str, Any]] = {}
        for key, payload_json in rows:
            output[str(key)] = json.loads(str(payload_json))
        return output
