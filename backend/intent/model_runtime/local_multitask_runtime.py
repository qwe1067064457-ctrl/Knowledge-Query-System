from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from intent.model_runtime.artifact_loader import IntentModelArtifacts


@dataclass(frozen=True)
class RuntimePrediction:
    multiclass_probs: dict[str, dict[str, float]]
    multilabel_scores: dict[str, dict[str, float]]


class LocalMultitaskRuntime:
    def __init__(
        self,
        *,
        artifacts: IntentModelArtifacts,
        max_length: int | None = None,
    ) -> None:
        self._artifacts = artifacts
        self._max_length = int(max_length or artifacts.config.get("max_length", 256))
        self._loaded = False
        self._torch: Any | None = None
        self._nn: Any | None = None
        self._tokenizer: Any | None = None
        self._encoder: Any | None = None
        self._dropout: Any | None = None
        self._multiclass_heads: Any | None = None
        self._multilabel_heads: Any | None = None
        self._device: Any | None = None

    def predict(self, text: str) -> RuntimePrediction:
        self._ensure_loaded()
        assert self._torch is not None
        assert self._tokenizer is not None
        assert self._encoder is not None
        assert self._dropout is not None
        assert self._multiclass_heads is not None
        assert self._multilabel_heads is not None
        assert self._device is not None

        encoded = self._tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self._max_length,
            return_tensors="pt",
        )
        input_ids = encoded["input_ids"].to(self._device)
        attention_mask = encoded["attention_mask"].to(self._device)

        with self._torch.no_grad():
            outputs = self._encoder(input_ids=input_ids, attention_mask=attention_mask)
            pooled = self._pool_outputs(outputs=outputs, attention_mask=attention_mask)
            pooled = self._dropout(pooled)
            multiclass_probs = {}
            for head, layer in self._multiclass_heads.items():
                logits = layer(self._align_hidden_dtype(pooled, layer))
                probs = self._torch.softmax(logits, dim=-1).detach().cpu()[0].tolist()
                labels = self._artifacts.label_spaces["multiclass_heads"][head]
                multiclass_probs[head] = {label: float(score) for label, score in zip(labels, probs)}

            multilabel_scores = {}
            for head, layer in self._multilabel_heads.items():
                logits = layer(self._align_hidden_dtype(pooled, layer))
                probs = self._torch.sigmoid(logits).detach().cpu()[0].tolist()
                labels = self._artifacts.label_spaces["multilabel_heads"][head]
                multilabel_scores[head] = {label: float(score) for label, score in zip(labels, probs)}

        return RuntimePrediction(
            multiclass_probs=multiclass_probs,
            multilabel_scores=multilabel_scores,
        )

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        deps = _import_runtime_dependencies()
        torch = deps["torch"]
        nn = deps["nn"]
        tokenizer = deps["AutoTokenizer"].from_pretrained(self._artifacts.model_dir)
        encoder = deps["AutoModel"].from_pretrained(self._artifacts.base_model_dir)
        if (self._artifacts.model_dir / "adapter_config.json").exists():
            encoder = deps["PeftModel"].from_pretrained(encoder, self._artifacts.model_dir)

        hidden_size = int(encoder.config.hidden_size)
        multiclass_heads = nn.ModuleDict(
            {
                head: nn.Linear(hidden_size, len(labels))
                for head, labels in self._artifacts.label_spaces["multiclass_heads"].items()
            }
        )
        multilabel_heads = nn.ModuleDict(
            {
                head: nn.Linear(hidden_size, len(labels))
                for head, labels in self._artifacts.label_spaces["multilabel_heads"].items()
            }
        )
        dropout = nn.Dropout(0.1)

        state_dict = torch.load(self._artifacts.model_dir / "multitask_heads.pt", map_location="cpu")
        multiclass_state = {
            key.removeprefix("multiclass_heads."): value
            for key, value in state_dict.items()
            if key.startswith("multiclass_heads.")
        }
        multilabel_state = {
            key.removeprefix("multilabel_heads."): value
            for key, value in state_dict.items()
            if key.startswith("multilabel_heads.")
        }
        dropout_state = {
            key.removeprefix("dropout."): value
            for key, value in state_dict.items()
            if key.startswith("dropout.")
        }
        multiclass_heads.load_state_dict(multiclass_state)
        multilabel_heads.load_state_dict(multilabel_state)
        if dropout_state:
            dropout.load_state_dict(dropout_state)

        device = torch.device("cpu")
        encoder.to(device)
        dropout.to(device)
        multiclass_heads.to(device)
        multilabel_heads.to(device)
        encoder.eval()
        dropout.eval()
        multiclass_heads.eval()
        multilabel_heads.eval()

        self._torch = torch
        self._nn = nn
        self._tokenizer = tokenizer
        self._encoder = encoder
        self._dropout = dropout
        self._multiclass_heads = multiclass_heads
        self._multilabel_heads = multilabel_heads
        self._device = device
        self._loaded = True

    def _pool_outputs(self, *, outputs: Any, attention_mask: Any) -> Any:
        pooled = getattr(outputs, "pooler_output", None)
        if pooled is not None:
            return pooled
        last_hidden_state = outputs.last_hidden_state
        model_type = str(getattr(self._encoder.config, "model_type", "")).lower()
        if model_type.startswith("qwen"):
            lengths = attention_mask.sum(dim=1) - 1
            batch_indices = self._torch.arange(last_hidden_state.size(0), device=last_hidden_state.device)
            return last_hidden_state[batch_indices, lengths]
        return last_hidden_state[:, 0]

    def _align_hidden_dtype(self, pooled: Any, layer: Any) -> Any:
        target_dtype = layer.weight.dtype
        if pooled.dtype == target_dtype:
            return pooled
        return pooled.to(dtype=target_dtype)


def _import_runtime_dependencies() -> dict[str, Any]:
    try:
        import torch
        import torch.nn as nn
        from peft import PeftModel
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("Intent local multitask runtime requires torch, transformers, and peft") from exc
    return {
        "torch": torch,
        "nn": nn,
        "PeftModel": PeftModel,
        "AutoModel": AutoModel,
        "AutoTokenizer": AutoTokenizer,
    }
