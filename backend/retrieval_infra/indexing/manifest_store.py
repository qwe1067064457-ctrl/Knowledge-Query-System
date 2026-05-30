from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from retrieval_infra.contracts import IndexManifest


class ManifestStore:
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = Path(manifest_path)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, namespace: str, *, default_active_slot: str = "current") -> IndexManifest:
        if not self.manifest_path.exists():
            return IndexManifest(namespace=namespace, active_slot=default_active_slot)
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return IndexManifest(
            namespace=str(payload.get("namespace", namespace)),
            active_slot=str(payload.get("active_slot", default_active_slot)),
            previous_slot=payload.get("previous_slot"),
            activated_at=payload.get("activated_at"),
            snapshot_id=payload.get("snapshot_id"),
        )

    def save(self, manifest: IndexManifest) -> None:
        self.manifest_path.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def switch(self, namespace: str, *, active_slot: str, previous_slot: str, snapshot_id: str | None = None) -> IndexManifest:
        manifest = IndexManifest(
            namespace=namespace,
            active_slot=active_slot,
            previous_slot=previous_slot,
            activated_at=datetime.now().isoformat(),
            snapshot_id=snapshot_id,
        )
        self.save(manifest)
        return manifest

    def rollback(self, namespace: str, *, active_slot: str, previous_slot: str | None, snapshot_id: str | None = None) -> IndexManifest:
        manifest = IndexManifest(
            namespace=namespace,
            active_slot=active_slot,
            previous_slot=previous_slot,
            activated_at=datetime.now().isoformat(),
            snapshot_id=snapshot_id,
        )
        self.save(manifest)
        return manifest
