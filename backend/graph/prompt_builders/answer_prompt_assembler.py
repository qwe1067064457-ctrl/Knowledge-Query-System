"""
Build the final prompt/messages for the main answer model.

This module combines:
- base answer system prompt,
- prepared conversation context,
- workflow-derived runtime instructions,
into the final input passed to the answer model.
"""
from __future__ import annotations

from pathlib import Path

from context.assembly.context_policy import ContextPolicyLoader


def _resolve_answer_system_prompt_path(base_dir: Path) -> Path:
    assembly_policy_path = base_dir / "context" / "assembly" / "context_policy.json"
    policy_loader = ContextPolicyLoader(assembly_policy_path)
    policy = policy_loader.load_policy()
    configured = str(policy.get("prompt", {}).get("system_prompt_path", "prompts/system/answer_system_prompt.md"))
    prompt_path = Path(configured)
    if prompt_path.is_absolute():
        return prompt_path
    return base_dir / prompt_path


def _resolve_runtime_override_path(base_dir: Path) -> Path:
    return base_dir / "prompts" / "system" / "runtime_override.md"


def build_answer_system_prompt(base_dir: Path, rag_mode: bool, extra_instructions: list[str] | None = None) -> str:
    del rag_mode
    prompt_path = _resolve_answer_system_prompt_path(base_dir)
    if prompt_path.exists():
        base_prompt = prompt_path.read_text(encoding="utf-8").strip()
    else:
        base_prompt = (
            "你是知识库问答系统中的核心问答助手。"
            "请基于提供的上下文、记忆和工具结果作答，不要编造事实。"
        )

    runtime_override_path = _resolve_runtime_override_path(base_dir)
    runtime_override = runtime_override_path.read_text(encoding="utf-8").strip() if runtime_override_path.exists() else ""

    sections = [base_prompt]
    if runtime_override:
        sections.append(runtime_override)
    if extra_instructions:
        sections.append("\n\n".join(extra_instructions))
    return "\n\n".join(section for section in sections if section).strip()


def assemble_answer_messages(
    base_dir: Path,
    messages: list[dict[str, str]],
    *,
    rag_mode: bool,
    extra_instructions: list[str] | None = None,
) -> list[dict[str, str]]:
    system_prompt = build_answer_system_prompt(base_dir, rag_mode, extra_instructions=extra_instructions)
    assembled: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    assembled.extend(messages)
    return assembled
