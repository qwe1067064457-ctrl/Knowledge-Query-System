from __future__ import annotations

from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.working_memory import evaluate_working_memory


def test_working_memory_template_entrypoint_fails_with_explicit_todo() -> None:
    with pytest.raises(SystemExit, match="TODO: working_memory evaluator is not implemented yet."):
        evaluate_working_memory.main()
