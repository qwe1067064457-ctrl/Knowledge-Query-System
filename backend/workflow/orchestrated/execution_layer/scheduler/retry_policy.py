from __future__ import annotations


class GroupRetryPolicy:
    def __init__(self, *, max_group_retries: int = 1) -> None:
        self.max_group_retries = max_group_retries

    def should_retry(self, *, states: tuple[str, ...], retry_count: int) -> bool:
        if retry_count >= self.max_group_retries:
            return False
        return any(state in {"failed", "degraded"} for state in states)

    def degraded_unit_ids(self, *, unit_results) -> tuple[str, ...]:
        return tuple(
            str(result.unit_id)
            for result in unit_results
            if getattr(result, "state", "") in {"failed", "degraded"}
        )
