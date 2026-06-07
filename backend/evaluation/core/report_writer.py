from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from .types import FinalEvalResult


class ReportWriter(Protocol):
    def summarize(self, results: Iterable[FinalEvalResult]) -> dict[str, Any]: ...

    def write(self, results: Iterable[FinalEvalResult], output_dir: str | Path) -> dict[str, Any]: ...


class StandardReportWriter:
    def __init__(
        self,
        *,
        summary_builder: Callable[[Iterable[dict[str, Any]]], dict[str, Any]],
        markdown_builder: Callable[[dict[str, Any]], str],
    ) -> None:
        self._summary_builder = summary_builder
        self._markdown_builder = markdown_builder

    def summarize(self, results: Iterable[FinalEvalResult]) -> dict[str, Any]:
        rows = [dict(item) for item in results]
        return self._summary_builder(rows)

    def write(self, results: Iterable[FinalEvalResult], output_dir: str | Path) -> dict[str, Any]:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        rows = [dict(item) for item in results]
        summary = self.summarize(rows)
        _save_results_jsonl(target_dir / "results.jsonl", rows)
        (target_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (target_dir / "report.md").write_text(self._markdown_builder(summary), encoding="utf-8")
        return summary


def _save_results_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    target.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
