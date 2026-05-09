from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


class MemoryPolicyLoader:
    def __init__(self, base_storage_path: Path, package_dir: Path | None = None) -> None:
        self.base_storage_path = Path(base_storage_path)
        self.package_dir = Path(package_dir) if package_dir else Path(__file__).resolve().parent
        self.default_policy_path = self.package_dir / "policy.default.json"

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _group_meta_path(self, group_id: str) -> Path:
        return self.base_storage_path / "groups" / group_id / "meta.json"

    def load_policy(self, group_id: str) -> Dict[str, Any]:
        default_payload = self._read_json(self.default_policy_path)
        default_policy = default_payload.get("memory_policy", {})

        group_meta = self._read_json(self._group_meta_path(group_id))
        group_policy = group_meta.get("memory_policy", {})

        return _deep_merge(default_policy, group_policy)
