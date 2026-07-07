from __future__ import annotations

from importlib import import_module

__all__ = ["knowledge_indexer"]


def __getattr__(name: str):
    if name == "knowledge_indexer":
        return import_module("knowledge_retrieval.indexer").knowledge_indexer
    raise AttributeError(name)
