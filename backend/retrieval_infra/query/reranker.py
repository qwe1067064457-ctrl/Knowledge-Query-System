from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path
from typing import Callable

from knowledge_retrieval.types import Evidence


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", text.lower())


class HeuristicCrossEncoderReranker:
    """启发式兜底 reranker。"""

    def rerank(self, query: str, evidences: list[Evidence], *, top_k: int) -> list[Evidence]:
        scored = [(self.score(query, item), item) for item in evidences]
        scored.sort(key=lambda item: item[0], reverse=True)
        output: list[Evidence] = []
        for score, evidence in scored[:top_k]:
            evidence.score = max(score, evidence.score or 0.0)
            output.append(evidence)
        return output

    def score(self, query: str, evidence: Evidence) -> float:
        query_terms = Counter(_tokenize(query))
        snippet_terms = Counter(_tokenize(evidence.snippet))
        path_terms = Counter(_tokenize(evidence.source_path))
        if not query_terms:
            return evidence.score or 0.0
        overlap = sum(min(count, snippet_terms.get(term, 0)) for term, count in query_terms.items())
        path_overlap = sum(min(count, path_terms.get(term, 0)) for term, count in query_terms.items())
        exact_phrase = 1.0 if re.sub(r"\s+", "", query.lower()) in re.sub(r"\s+", "", evidence.snippet.lower()) else 0.0
        base = (evidence.score or 0.0) * 0.55
        lexical = overlap / max(1, sum(query_terms.values()))
        return round(base + lexical * 0.3 + (path_overlap / max(1, sum(query_terms.values()))) * 0.1 + exact_phrase * 0.05, 6)


class LocalCrossEncoderReranker:
    """本地 cross-encoder 优先；未配置本地模型时回退到 heuristic。"""

    def __init__(self, model_ref: str | None = None, *, max_length: int = 512) -> None:
        self.model_ref = model_ref or os.getenv("RETRIEVAL_CROSS_ENCODER_MODEL") or ""
        self.max_length = max_length
        self.heuristic = HeuristicCrossEncoderReranker()
        self._score_pairs_impl: Callable[[str, list[Evidence]], list[float]] | None = None
        self._model_origin: str | None = None

    @property
    def active_backend(self) -> str:
        self._ensure_backend()
        return self._model_origin or "heuristic"

    def rerank(self, query: str, evidences: list[Evidence], *, top_k: int) -> list[Evidence]:
        if not evidences:
            return []
        self._ensure_backend()
        if self._score_pairs_impl is None:
            return self.heuristic.rerank(query, evidences, top_k=top_k)
        scores = self._score_pairs_impl(query, evidences)
        scored = list(zip(scores, evidences))
        scored.sort(key=lambda item: item[0], reverse=True)
        output: list[Evidence] = []
        for score, evidence in scored[:top_k]:
            evidence.score = max(float(score), evidence.score or 0.0)
            output.append(evidence)
        return output

    def _ensure_backend(self) -> None:
        if self._score_pairs_impl is not None or self._model_origin is not None:
            return
        model_path = self._discover_local_model()
        if model_path is None:
            self._model_origin = "heuristic"
            return
        scorer = self._load_local_cross_encoder(model_path)
        if scorer is None:
            self._model_origin = "heuristic"
            return
        self._score_pairs_impl = scorer
        self._model_origin = str(model_path)

    def _discover_local_model(self) -> Path | None:
        if self.model_ref:
            candidate = Path(self.model_ref)
            if candidate.exists() and self._looks_like_hf_model_dir(candidate):
                return candidate
            return None

        candidates: list[Path] = []

        backend_root = Path(__file__).resolve().parents[2]
        candidates.extend(
            [
                backend_root / "models" / "reranker",
                backend_root / "models" / "bge-reranker-base",
                backend_root.parent / "models" / "reranker",
                backend_root.parent / "models" / "bge-reranker-base",
            ]
        )

        hub_root = Path.home() / ".cache" / "huggingface" / "hub"
        for model_dir in (
            hub_root / "models--BAAI--bge-reranker-base",
            hub_root / "models--BAAI--bge-reranker-large",
            hub_root / "models--cross-encoder--ms-marco-MiniLM-L-6-v2",
        ):
            snapshots_dir = model_dir / "snapshots"
            if snapshots_dir.exists():
                for child in sorted(snapshots_dir.iterdir()):
                    if child.is_dir():
                        candidates.append(child)

        for candidate in candidates:
            if candidate.exists() and self._looks_like_hf_model_dir(candidate):
                return candidate
        return None

    @staticmethod
    def _looks_like_hf_model_dir(path: Path) -> bool:
        return (path / "config.json").exists() and any(
            (path / name).exists() for name in ("model.safetensors", "pytorch_model.bin", "tokenizer.json", "vocab.txt")
        )

    def _load_local_cross_encoder(self, model_path: Path) -> Callable[[str, list[Evidence]], list[float]] | None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except Exception:
            return None

        try:
            tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(str(model_path), local_files_only=True)
            model.eval()
        except Exception:
            return None

        def score_pairs(query: str, evidences: list[Evidence]) -> list[float]:
            pairs = [(query, evidence.snippet) for evidence in evidences]
            with torch.no_grad():
                encoded = tokenizer(
                    pairs,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                )
                logits = model(**encoded).logits
                if logits.ndim == 2 and logits.shape[-1] > 1:
                    scores_tensor = logits[:, -1]
                else:
                    scores_tensor = logits.reshape(-1)
                return [float(value) for value in scores_tensor.detach().cpu().tolist()]

        return score_pairs
