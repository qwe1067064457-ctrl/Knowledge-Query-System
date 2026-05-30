from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional

from memory_system.jobs.memory_write_queue import MemoryWriteQueue


class MemoryWriteWorker:
    def __init__(self, queue: MemoryWriteQueue) -> None:
        self.queue = queue

    async def drain(self, handler: Callable[[Dict[str, Any]], None]) -> int:
        written = 0
        while True:
            payload = self.queue.pop()
            if payload is None:
                break
            handler(payload)
            written += 1
        return written
