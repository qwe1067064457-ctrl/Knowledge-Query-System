from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def tmp_path() -> Path:
    temp_root = ROOT / "backend" / ".test_tmp" / "workflow_cases"
    temp_root.mkdir(parents=True, exist_ok=True)
    directory = temp_root / f"case_{uuid.uuid4().hex}"
    directory.mkdir(parents=True, exist_ok=False)
    return directory
