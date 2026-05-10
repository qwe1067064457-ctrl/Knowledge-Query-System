from __future__ import annotations

from pathlib import Path

from context.context_policy import ContextPolicyLoader

RUNTIME_OVERRIDE = """<!-- Runtime Override -->
When explicit retrieval evidence is provided for the current request, prioritize that evidence.
Do not assume missing evidence exists elsewhere.
"""


def _resolve_system_prompt_path(base_dir: Path) -> Path:
    policy_loader = ContextPolicyLoader(base_dir / "context" / "context_policy.json")
    policy = policy_loader.load_policy()
    configured = str(policy.get("prompt", {}).get("system_prompt_path", "prompts/system_prompt.md"))
    prompt_path = Path(configured)
    if prompt_path.is_absolute():
        return prompt_path
    return base_dir / prompt_path


def build_system_prompt(base_dir: Path, rag_mode: bool) -> str:
    del rag_mode
    prompt_path = _resolve_system_prompt_path(base_dir)
    if prompt_path.exists():
        content = prompt_path.read_text(encoding="utf-8").strip()
    else:
        content = (
            "你是知识库问答系统中的核心问答助手。"
            "请基于提供的上下文、记忆和工具结果作答，不要编造事实。"
        )
    return f"{content}\n\n{RUNTIME_OVERRIDE}"
