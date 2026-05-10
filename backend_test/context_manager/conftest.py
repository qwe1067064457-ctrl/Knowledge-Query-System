from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from helpers import TEST_TMP_ROOT, temp_workspace


@pytest.fixture
def workspace() -> Path:
    with temp_workspace() as path:
        yield path


def pytest_sessionfinish(session, exitstatus):  # type: ignore[no-untyped-def]
    try:
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)
    except OSError:
        pass
