from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, Optional


class MemoryWriteQueue:
    def __init__(self) -> None:
        self._queue: Deque[Dict[str, Any]] = deque()

    def enqueue(self, payload: Dict[str, Any]) -> None:
        self._queue.append(dict(payload))

    def pop(self) -> Optional[Dict[str, Any]]:
        if not self._queue:
            return None
        return self._queue.popleft()

    def __len__(self) -> int:
        return len(self._queue)
