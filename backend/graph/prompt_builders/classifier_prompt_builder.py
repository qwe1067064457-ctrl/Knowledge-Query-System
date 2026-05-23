"""
Load classifier prompt text for router or intent-classifier style components.
"""
from __future__ import annotations

from pathlib import Path


def load_intent_classifier_prompt(base_dir: Path) -> str:
    prompt_path = base_dir / "prompts" / "classifiers" / "intent_classifier_prompt.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return ""
