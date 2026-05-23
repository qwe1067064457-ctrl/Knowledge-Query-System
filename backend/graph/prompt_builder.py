from __future__ import annotations

from pathlib import Path

from graph.prompt_builders.answer_prompt_assembler import build_answer_system_prompt


def build_system_prompt(base_dir: Path, rag_mode: bool) -> str:
    return build_answer_system_prompt(base_dir, rag_mode, extra_instructions=None)
