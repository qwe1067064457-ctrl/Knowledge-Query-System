from __future__ import annotations

from functools import wraps
from typing import Any, Callable


def traceable_passthrough(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return _wrapper
