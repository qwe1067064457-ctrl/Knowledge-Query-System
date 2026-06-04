from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl_cases(path: str | Path) -> list[dict[str, Any]]:
    root = Path(path)
    if root.is_dir():
        paths = sorted(root.glob("*.jsonl"))
    else:
        paths = [root]

    rows: list[dict[str, Any]] = []
    for case_path in paths:
        for line_no, line in enumerate(case_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Case line must be an object: {case_path}:{line_no}")
            rows.append(payload)
    return rows
