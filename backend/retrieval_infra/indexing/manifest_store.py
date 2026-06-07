from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from retrieval_infra.contracts import IndexManifest


class ManifestStore:
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = Path(manifest_path)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, namespace: str) -> IndexManifest:
        if not self.manifest_path.exists():
            return IndexManifest(namespace=namespace)
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return IndexManifest(
            namespace=str(payload.get("namespace", namespace)),
            current_build_id=payload.get("current_build_id"),
            current_snapshot_id=payload.get("current_snapshot_id"),
            previous_snapshot_id=payload.get("previous_snapshot_id"),
            activated_at=payload.get("activated_at"),
        )

    def save(self, manifest: IndexManifest) -> None:
        self.manifest_path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def activate(
        self,
        namespace: str,
        *,
        current_build_id: str,
        current_snapshot_id: str,
        previous_snapshot_id: str | None = None,
    ) -> IndexManifest:
        manifest = IndexManifest(
            namespace=namespace,
            current_build_id=current_build_id,
            current_snapshot_id=current_snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            activated_at=datetime.now().isoformat(),
        )
        self.save(manifest)
        return manifest

    def rollback(
        self,
        namespace: str,
        *,
        current_build_id: str,
        current_snapshot_id: str,
        previous_snapshot_id: str | None = None,
    ) -> IndexManifest:
        manifest = IndexManifest(
            namespace=namespace,
            current_build_id=current_build_id,
            current_snapshot_id=current_snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            activated_at=datetime.now().isoformat(),
        )
        self.save(manifest)
        return manifest
