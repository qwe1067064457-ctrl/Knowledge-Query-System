from __future__ import annotations

from importlib import import_module

__all__ = ["knowledge_indexer", "knowledge_orchestrator"]


def __getattr__(name: str):
    if name == "knowledge_indexer":
        return import_module("knowledge_retrieval.indexer").knowledge_indexer
    if name == "knowledge_orchestrator":
        return import_module("knowledge_retrieval.orchestrator").knowledge_orchestrator
    raise AttributeError(name)
