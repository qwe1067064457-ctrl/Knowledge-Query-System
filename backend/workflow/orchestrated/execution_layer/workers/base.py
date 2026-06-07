from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class WorkerSpec:
    name: str
    description: str
    callable: Callable[..., Any]


class BaseWorker:
    name = "base_worker"
    description = "Base execution worker."

    def as_spec(self) -> WorkerSpec:
        return WorkerSpec(
            name=self.name,
            description=self.description,
            callable=self.run,
        )

    def run(self, **kwargs):
        raise NotImplementedError

