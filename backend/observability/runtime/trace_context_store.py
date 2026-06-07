from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from observability.contracts.trace_context import TraceContext

_CURRENT_TRACE_CONTEXT: ContextVar[TraceContext | None] = ContextVar(
    "observability_current_trace_context",
    default=None,
)


def get_current_trace_context() -> TraceContext | None:
    return _CURRENT_TRACE_CONTEXT.get()


@contextmanager
def activate_trace_context(trace_context: TraceContext) -> Iterator[TraceContext]:
    token = _CURRENT_TRACE_CONTEXT.set(trace_context)
    try:
        yield trace_context
    finally:
        _CURRENT_TRACE_CONTEXT.reset(token)
