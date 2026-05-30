from __future__ import annotations

import json
from pathlib import Path

from retrieval_infra.contracts import BuildCheckpoint, BuildRequest


class StateStore:
    def __init__(self, *, build_registry_path: Path, checkpoints_path: Path) -> None:
        self.build_registry_path = Path(build_registry_path)
        self.checkpoints_path = Path(checkpoints_path)
        self.build_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoints_path.parent.mkdir(parents=True, exist_ok=True)

    def append_build(self, request: BuildRequest, *, status: str) -> None:
        payload = request.to_dict() | {"status": status}
        with self.build_registry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def write_checkpoint(self, checkpoint: BuildCheckpoint) -> None:
        checkpoints = self.load_checkpoints()
        checkpoints[checkpoint.source_id] = checkpoint.to_dict()
        self.checkpoints_path.write_text(json.dumps(checkpoints, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_checkpoints(self) -> dict[str, dict[str, object]]:
        if not self.checkpoints_path.exists():
            return {}
        return json.loads(self.checkpoints_path.read_text(encoding="utf-8"))
