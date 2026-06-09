from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_RUNTIME_LABEL_SPACES: dict[str, dict[str, list[str]]] = {
    "multiclass_heads": {
        "main_intent": ["qa", "chat", "system", "unsupported"],
        "task_complexity": ["simple", "compound", "complex"],
        "task_shape": ["none", "single_question", "verify", "compare", "summarize", "multi_question", "mixed"],
        "task_topology": ["single", "parallel_queries", "parallel_subtasks", "staged"],
        "context_dependency": ["none", "partial", "global"],
        "handling_mode": ["normal", "challenge", "clarify", "scope_info", "unsupported"],
    },
    "multilabel_heads": {
        "modifiers": [
            "follow_up",
            "challenge",
            "soft_doubt",
            "ask_source",
            "ask_capability",
            "needs_clarification",
            "out_of_scope",
        ],
        "context": [
            "history_reference",
            "needs_previous_answer",
            "previous_retrieval",
            "clarify_hint",
        ],
        "safety": ["unsupported", "out_of_scope"],
        "ambiguity_states": [
            "referent_ambiguity",
            "target_ambiguity",
            "scope_ambiguity",
            "missing_context",
        ],
    },
}


@dataclass(frozen=True)
class IntentModelArtifacts:
    run_dir: Path
    model_dir: Path
    config: dict[str, Any]
    thresholds: dict[str, Any]
    label_spaces: dict[str, dict[str, list[str]]]
    base_model_dir: Path


def load_intent_model_artifacts(
    run_dir: Path,
    *,
    project_root: Path,
) -> IntentModelArtifacts:
    resolved_run_dir = run_dir.expanduser().resolve()
    model_dir = resolved_run_dir / "model"
    config = _read_json(resolved_run_dir / "config.json", required=True)
    thresholds = _read_json(resolved_run_dir / "thresholds.json", required=True)
    label_spaces = _resolve_label_spaces(resolved_run_dir=resolved_run_dir, project_root=project_root, config=config)
    base_model_dir = _resolve_base_model_dir(project_root=project_root, config=config)
    return IntentModelArtifacts(
        run_dir=resolved_run_dir,
        model_dir=model_dir,
        config=config,
        thresholds=thresholds,
        label_spaces=label_spaces,
        base_model_dir=base_model_dir,
    )


def _resolve_label_spaces(
    *,
    resolved_run_dir: Path,
    project_root: Path,
    config: dict[str, Any],
) -> dict[str, dict[str, list[str]]]:
    direct_path = resolved_run_dir / "label_spaces.json"
    if direct_path.exists():
        return _read_json(direct_path, required=True)

    bundle_dir = str(config.get("bundle_dir", "")).strip()
    if bundle_dir:
        bundle_label_path = project_root / "evaluation" / "intent" / "v2_sft" / bundle_dir / "label_spaces.json"
        if bundle_label_path.exists():
            return _read_json(bundle_label_path, required=True)

    return DEFAULT_RUNTIME_LABEL_SPACES


def _resolve_base_model_dir(*, project_root: Path, config: dict[str, Any]) -> Path:
    configured = str(config.get("model_name", "")).strip()
    if not configured:
        raise RuntimeError("Missing model_name in intent model config")

    configured_path = Path(configured).expanduser()
    if configured_path.is_absolute() and configured_path.exists():
        return configured_path.resolve()

    relative_candidate = (project_root / configured_path).resolve()
    if relative_candidate.exists():
        return relative_candidate

    backend_candidate = (project_root / "backend" / "models" / configured).resolve()
    if backend_candidate.exists():
        return backend_candidate

    raise RuntimeError(f"Unable to resolve base model path from model_name={configured!r}")


def _read_json(path: Path, *, required: bool) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise RuntimeError(f"Missing required model artifact: {path}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
