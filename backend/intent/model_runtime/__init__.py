from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from intent.model_runtime.artifact_loader import IntentModelArtifacts, load_intent_model_artifacts
from intent.model_runtime.fallback_policy import INTENT_LLM_FALLBACK_ENV, is_llm_fallback_enabled, should_trigger_llm_fallback
from intent.model_runtime.llm_fallback_adapter import IntentLLMFallbackAdapter, LLMIntentFallbackAdapter
from intent.model_runtime.local_multitask_runtime import LocalMultitaskRuntime
from intent.model_runtime.small_model_adapter import LocalIntentModelAdapter


@lru_cache(maxsize=1)
def build_default_small_model_adapter(
    *,
    project_root: Path,
    run_dir: Path | None = None,
) -> LocalIntentModelAdapter:
    resolved_run_dir = run_dir or project_root / "backend" / "models" / "v6"
    artifacts = load_intent_model_artifacts(resolved_run_dir, project_root=project_root)
    runtime = LocalMultitaskRuntime(artifacts=artifacts)
    return LocalIntentModelAdapter(runtime=runtime, thresholds=artifacts.thresholds)


@lru_cache(maxsize=1)
def build_default_llm_fallback_adapter(
    *,
    project_root: Path,
) -> IntentLLMFallbackAdapter:
    prompt_path = project_root / "backend" / "intent" / "prompts" / "intent_fallback.md"
    return LLMIntentFallbackAdapter(prompt_path=prompt_path)


__all__ = [
    "INTENT_LLM_FALLBACK_ENV",
    "IntentLLMFallbackAdapter",
    "IntentModelArtifacts",
    "LLMIntentFallbackAdapter",
    "LocalIntentModelAdapter",
    "LocalMultitaskRuntime",
    "build_default_llm_fallback_adapter",
    "build_default_small_model_adapter",
    "is_llm_fallback_enabled",
    "load_intent_model_artifacts",
    "should_trigger_llm_fallback",
]
