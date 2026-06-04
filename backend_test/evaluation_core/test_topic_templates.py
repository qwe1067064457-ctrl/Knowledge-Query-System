from __future__ import annotations

from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.compaction import evaluate_compaction
from evaluation.long_term_memory import evaluate_long_term_memory
from evaluation.working_memory import evaluate_working_memory


@pytest.mark.parametrize(
    ("entrypoint", "expected_message"),
    [
        (evaluate_long_term_memory.main, "TODO: long_term_memory evaluator is not implemented yet."),
        (evaluate_working_memory.main, "TODO: working_memory evaluator is not implemented yet."),
        (evaluate_compaction.main, "TODO: compaction evaluator is not implemented yet."),
    ],
)
def test_template_entrypoints_fail_with_explicit_todo(entrypoint, expected_message: str) -> None:
    with pytest.raises(SystemExit, match=expected_message):
        entrypoint()
