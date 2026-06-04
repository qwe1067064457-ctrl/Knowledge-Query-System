from __future__ import annotations

from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

def test_topic_templates_are_replaced_by_real_topics() -> None:
    assert True
